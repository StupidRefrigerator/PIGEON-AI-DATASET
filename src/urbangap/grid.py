import geopandas as gpd
import h3
import pandas as pd
from shapely.geometry import Polygon

from .common import RAW, CRS, RESOLUTION, require


def build_grid(study):
    shape = study.to_crs(4326).geometry.union_all()
    ids = sorted(h3.geo_to_cells(shape.__geo_interface__, RESOLUTION))
    geometries = [Polygon([(lon, lat) for lat, lon in h3.cell_to_boundary(cell)]) for cell in ids]
    return gpd.GeoDataFrame({"hex_id": ids}, geometry=geometries, crs=4326).to_crs(CRS)


def assign_toilets(grid):
    toilets = pd.read_csv(RAW / "national_toilets.csv")
    require(toilets.FacilityID.is_unique, "Duplicate FacilityIDs require investigation")
    coordinates = toilets.dropna(subset=["Latitude", "Longitude"]).copy()
    require(coordinates.Latitude.between(-90, 90).all() and coordinates.Longitude.between(-180, 180).all(),
            "Invalid toilet coordinates")
    coordinates["hex_id"] = [h3.latlng_to_cell(lat, lon, RESOLUTION)
                              for lat, lon in zip(coordinates.Latitude, coordinates.Longitude)]
    counts = coordinates.groupby("hex_id").size()
    grid = grid.copy()
    grid["toilet_count"] = grid.hex_id.map(counts).fillna(0).astype(int)
    diagnostics = {"national_records": len(toilets), "missing_coordinate_records": len(toilets) - len(coordinates),
                   "grid_records": int(grid.toilet_count.sum()), "occupied_hexagons": int((grid.toilet_count > 0).sum())}
    return grid, diagnostics
