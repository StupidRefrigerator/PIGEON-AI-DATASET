"""Reconstructed OSM preparation and feature definitions from the saved notebooks."""
import hashlib
import re
import shutil
import subprocess

import geopandas as gpd
import pandas as pd
from shapely import area, buffer, intersection
from shapely.geometry import box

from .common import RAW, INTERIM, CRS, RADII, require, write_json

BBOX = "150.45,-34.25,151.40,-33.35"
FILTERS = ["nwr/shop", "nwr/amenity=cafe,restaurant", "nwr/highway=bus_stop",
           "nwr/railway=station", "nwr/leisure=park"]
CATEGORIES = {"shop": "is_active_shop", "food": "is_food", "bus_stop": "is_bus_stop",
              "train_station": "is_train_station"}


def object_digest(path):
    """Hash canonical OPL objects, independent of PBF compression/header differences."""
    process = subprocess.Popen(["osmium", "cat", str(path), "-f", "opl"], stdout=subprocess.PIPE)
    digest = hashlib.sha256()
    with process.stdout as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    require(process.wait() == 0, f"Cannot inspect OSM objects: {path}")
    return digest.hexdigest()


def prepare_osm():
    for tool in ("osmium", "ogr2ogr"):
        require(shutil.which(tool) is not None, f"Install native tool {tool}; see README.md")
    folder = INTERIM / "osm"
    folder.mkdir(parents=True, exist_ok=True)
    sydney, pois, gpkg = (folder / n for n in ("sydney.osm.pbf", "sydney_pois.osm.pbf", "sydney_pois.gpkg"))
    commands = [
        ["osmium", "extract", "-b", BBOX, "-s", "complete_ways", str(RAW / "osm/nsw.osm.pbf"), "-o", str(sydney), "--overwrite"],
        ["osmium", "tags-filter", str(sydney), *FILTERS, "-o", str(pois), "--overwrite"],
        ["ogr2ogr", "-f", "GPKG", "-overwrite", str(gpkg), str(pois)],
    ]
    for command in commands:
        subprocess.run(command, check=True, cwd=folder)
    checks = {}
    for rebuilt, original in [(sydney, RAW / "osm/sydney.osm.pbf"), (pois, RAW / "osm/sydney_pois.osm.pbf")]:
        digest = object_digest(rebuilt)
        checks[rebuilt.name] = {"canonical_sha256": digest, "matches_preserved_extract": digest == object_digest(original)}
        require(checks[rebuilt.name]["matches_preserved_extract"], f"Rebuilt OSM differs from preserved extract: {original}")
    write_json(folder / "preparation.json", {"commands": commands, "object_comparisons": checks,
               "osmium_version": subprocess.check_output(["osmium", "--version"], text=True).splitlines()[0],
               "gdal_version": subprocess.check_output(["ogr2ogr", "--version"], text=True).strip()})
    return gpkg


def get_tag(value, key):
    if pd.isna(value):
        return None
    # Preserve the original GDAL hstore parsing semantics.
    match = re.search(rf'"{re.escape(key)}"=>"([^"]*)"', str(value))
    return match.group(1) if match else None


def load_objects(path):
    points = gpd.read_file(path, layer="points")
    polygons = gpd.read_file(path, layer="multipolygons")
    for frame in (points, polygons):
        for tag in ("shop", "amenity", "highway", "railway", "leisure"):
            extracted = frame.other_tags.map(lambda value: get_tag(value, tag))
            frame[tag] = frame[tag].fillna(extracted) if tag in frame else extracted
    representative = polygons.copy()
    # Preserve historical order: representative point in source CRS, THEN project.
    representative.geometry = representative.representative_point()
    objects = gpd.GeoDataFrame(pd.concat([points, representative], ignore_index=True),
                               geometry="geometry", crs=points.crs).to_crs(CRS)
    for name, values in {
        "is_active_shop": objects.shop.notna() & objects.shop.ne("vacant"),
        "is_food": objects.amenity.isin(["cafe", "restaurant"]),
        "is_bus_stop": objects.highway.eq("bus_stop"),
        "is_train_station": objects.railway.eq("station"),
    }.items():
        objects[name] = values.fillna(False)
    parks = polygons[polygons.leisure.eq("park")].to_crs(CRS).copy()
    parks = parks[parks.geometry.notna() & ~parks.is_empty].copy()
    parks.geometry = parks.make_valid()
    require(parks.geom_type.isin(["Polygon", "MultiPolygon"]).all(),
            "Park repair produced non-polygon geometry; investigate before dropping data")
    return objects, parks


def add_count_features(grid, objects):
    grid = grid.copy()
    nearby = objects[objects.intersects(grid.geometry.union_all().buffer(500))].copy()
    inside = gpd.sjoin(nearby, grid[["hex_id", "geometry"]], how="inner", predicate="within")
    centres = grid[["hex_id", "geometry"]].copy()
    centres.geometry = centres.centroid
    for category, flag in CATEGORIES.items():
        counts = inside.loc[inside[flag]].groupby("hex_id").size()
        grid[f"{category}_inside"] = grid.hex_id.map(counts).fillna(0).astype(int)
        selected = nearby.loc[nearby[flag], ["geometry"]]
        for radius in RADII:
            zones = centres.copy()
            zones.geometry = zones.buffer(radius)
            joined = gpd.sjoin(zones, selected, how="left", predicate="intersects")
            counts = joined.groupby("hex_id").index_right.count()
            grid[f"{category}_{radius}m"] = grid.hex_id.map(counts).fillna(0).astype(int)
    return grid, {"context_objects": len(nearby),
                  **{flag: int(nearby[flag].sum()) for flag in CATEGORIES.values()}}


def add_park_features(grid, parks):
    grid = grid.copy()
    # Context restriction remains ONLY for park area: reproduce the approved areas.
    nearby = parks[parks.intersects(grid.geometry.union_all().buffer(500))]
    combined = nearby.geometry.union_all()
    grid["park_area_inside_m2"] = area(intersection(grid.geometry.array, combined))
    centres = grid.centroid
    for radius in RADII:
        # Shapely default: 8 segments/quadrant, as in the original park notebook.
        zones = buffer(centres.array, radius)
        grid[f"park_area_{radius}m_m2"] = area(intersection(zones, combined))
    # Spatial index over ALL available park polygons; ties collapse to one distance.
    centre_frame = gpd.GeoDataFrame(grid[["hex_id"]].copy(), geometry=centres, crs=CRS)
    nearest = gpd.sjoin_nearest(centre_frame, parks[["geometry"]], how="left", distance_col="distance_m")
    distances = nearest.groupby("hex_id").distance_m.min()
    grid["distance_nearest_park_m"] = grid.hex_id.map(distances)
    require(grid.distance_nearest_park_m.notna().all(), "Nearest park missing")
    extraction = gpd.GeoSeries([box(150.45, -34.25, 151.40, -33.35)], crs=4326).to_crs(CRS).iloc[0]
    # Geometric check, not a claim of complete OSM mapping or relation extraction.
    distance_to_edge = centres.distance(extraction.boundary)
    margin = distance_to_edge - grid.distance_nearest_park_m
    coverage = {"available_park_polygons": len(parks), "area_context_parks": len(nearby),
                "extraction_bbox_wgs84": [150.45, -34.25, 151.40, -33.35],
                "centres_inside_extraction_bbox": int(centres.within(extraction).sum()),
                "nearest_distance_below_bbox_edge_distance": int((margin > 0).sum()),
                "minimum_edge_distance_minus_nearest_distance_m": float(margin.min()),
                "scope": "nearest among available extracted park polygons; OSM completeness and complete relation coverage are not guaranteed"}
    return grid, coverage
