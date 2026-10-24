import geopandas as gpd
import h3
import pandas as pd
from shapely.geometry import Polygon

from .paths import CRS, RAW, REFERENCE


def load_population_boundaries():
    census_folder = RAW / "census_2021"
    census_table = "2021 Census GCP Statistical Area 1 for NSW"
    census_path = census_folder / census_table / "2021Census_G01_NSW_SA1.csv"
    population = pd.read_csv(
        census_path,
        usecols=["SA1_CODE_2021", "Tot_P_P"],
        dtype={"SA1_CODE_2021": str},
    )
    population.columns = ["sa1_code", "population"]

    boundary_path = RAW / "abs_sa1_2021/SA1_2021_AUST_GDA2020.shp"
    boundaries = gpd.read_file(boundary_path)
    boundaries["sa1_code"] = boundaries["SA1_CODE21"].astype(str)
    return boundaries.merge(
        population, on="sa1_code", how="left", validate="one_to_one"
    )


def build_study_area(boundaries):
    sydney = boundaries[boundaries["GCC_NAME21"] == "Greater Sydney"]
    approved_ids = (REFERENCE / "approved_preliminary_sa1_ids.txt")
    preliminary_ids = approved_ids.read_text().splitlines()

    # The historical 50-person density selection is frozen in this registry.
    selected = sydney["sa1_code"].isin(preliminary_ids)
    preliminary = sydney[selected].to_crs(CRS).copy()

    boundary_path = RAW / "abs_boundaries/GCCSA_2026_AUST_GDA2020.shp"
    city_boundaries = gpd.read_file(boundary_path)
    city_boundary = city_boundaries[
        city_boundaries["GCC_NAME26"] == "Greater Sydney"
    ]
    suburb_path = RAW / "abs_suburbs/SAL_2026_AUST_GDA2020.shp"
    suburbs = gpd.read_file(suburb_path).to_crs(city_boundary.crs)
    suburbs = suburbs[suburbs["STE_NAME26"] == "New South Wales"]
    suburb_points = suburbs.representative_point()
    city_shape = city_boundary.geometry.union_all()
    suburbs = suburbs[suburb_points.intersects(city_shape)]

    growth_names = (REFERENCE / "growth_suburbs.txt").read_text().splitlines()
    growth_suburbs = suburbs[suburbs["SAL_NAME26"].isin(growth_names)]
    assert set(growth_suburbs["SAL_NAME26"]) == set(growth_names), (
        "Some growth-suburb names did not match the source boundaries"
    )
    growth_suburbs = growth_suburbs.to_crs(CRS)
    growth_area = growth_suburbs.geometry.union_all()
    sa1_points = preliminary.representative_point()
    in_growth_area = sa1_points.intersects(growth_area)
    study = preliminary[~in_growth_area].copy()
    print(
        f"Study area: {len(preliminary):,} preliminary SA1s, "
        f"{len(study):,} after growth-suburb exclusions",
        flush=True,
    )
    return study


def build_grid(study):
    study_shape = study.to_crs(4326).geometry.union_all()
    hex_ids = sorted(h3.geo_to_cells(study_shape.__geo_interface__, res=9))
    polygons = []
    for hex_id in hex_ids:
        coordinates = []
        for latitude, longitude in h3.cell_to_boundary(hex_id):
            coordinates.append((longitude, latitude))
        polygons.append(Polygon(coordinates))

    grid = gpd.GeoDataFrame(
        {"hex_id": hex_ids}, geometry=polygons, crs="EPSG:4326"
    )
    return grid.to_crs(CRS)


def add_toilet_counts(grid):
    toilets = pd.read_csv(RAW / "national_toilets.csv")
    assert toilets["FacilityID"].is_unique, "Duplicate toilet facility IDs"
    toilets = toilets.dropna(subset=["Latitude", "Longitude"]).copy()
    hex_ids = []
    for latitude, longitude in zip(toilets["Latitude"], toilets["Longitude"]):
        hex_ids.append(h3.latlng_to_cell(latitude, longitude, 9))
    toilets["hex_id"] = hex_ids
    counts = toilets.groupby("hex_id").size()

    grid = grid.copy()
    grid["toilet_count"] = grid["hex_id"].map(counts).fillna(0).astype(int)
    return grid
