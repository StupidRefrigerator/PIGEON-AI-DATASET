import geopandas as gpd
import numpy as np
import pandas as pd
from shapely import area, buffer

from .paths import BASELINE, INTERIM, PROCESSED, REFERENCE

FEATURES = [
    "population_est",
    "population_density",
    "shop_inside",
    "shop_250m",
    "shop_500m",
    "food_inside",
    "food_250m",
    "food_500m",
    "bus_stop_inside",
    "bus_stop_250m",
    "bus_stop_500m",
    "train_station_inside",
    "train_station_250m",
    "train_station_500m",
    "park_area_inside_m2",
    "park_area_250m_m2",
    "park_area_500m_m2",
    "distance_nearest_park_m",
    "population_250m",
    "population_500m",
]
COLUMNS = ["hex_id", "toilet_count"] + FEATURES + ["geometry"]
TOLERANCE = 1e-6


def validate_features(features):
    assert list(features.columns) == COLUMNS, "Unexpected final feature schema"
    assert features.crs.to_epsg() == 7856, "Metric geometry must use EPSG:7856"
    assert len(features) == 16228, "Expected 16,228 hexagons"
    assert features["hex_id"].is_unique, "Duplicate hexagon IDs"
    approved_path = REFERENCE / "approved_hex_ids.txt"
    approved_ids = set(approved_path.read_text().splitlines())
    assert set(features["hex_id"]) == approved_ids, "Approved H3 membership changed"
    assert features.geometry.notna().all(), "Missing geometry"
    assert features.is_valid.all() and not features.is_empty.any(), "Invalid geometry"

    numbers = features.drop(columns=["hex_id", "geometry"])
    assert np.isfinite(numbers.to_numpy()).all(), "Missing or infinite feature values"
    assert (numbers >= 0).all().all(), "Negative feature values"
    assert features["toilet_count"].sum() == 2570, "Expected 2,570 toilet records"
    occupied = features["toilet_count"] > 0
    assert occupied.sum() == 1911, "Expected 1,911 occupied hexagons"

    hex_population = features["population_est"]
    population_250 = features["population_250m"]
    population_500 = features["population_500m"]
    assert (population_500 + TOLERANCE >= population_250).all(), (
        "500 m population is smaller than 250 m population"
    )
    assert (population_250 + TOLERANCE >= hex_population).all(), (
        "250 m population is smaller than hexagon population"
    )
    expected_density = hex_population / (features.geometry.area / 1_000_000)
    np.testing.assert_allclose(
        features["population_density"], expected_density, rtol=1e-10, atol=TOLERANCE
    )

    assert (features["park_area_inside_m2"] <= features.area + TOLERANCE).all(), (
        "Park footprint exceeds its hexagon"
    )
    for radius in (250, 500):
        buffer_area = area(buffer(features.centroid.array, radius))
        park_area = features[f"park_area_{radius}m_m2"]
        assert (park_area <= buffer_area + TOLERANCE).all(), (
            f"Park footprint exceeds its {radius} m buffer"
        )
    assert (
        features["park_area_500m_m2"] + TOLERANCE
        >= features["park_area_250m_m2"]
    ).all(), "Park buffer areas are not nested"
    assert (
        features["park_area_250m_m2"] + TOLERANCE
        >= features["park_area_inside_m2"]
    ).all(), "Hexagon park area exceeds the containing 250 m buffer"

    for category in ("shop", "food", "bus_stop", "train_station"):
        assert (features[f"{category}_500m"] >= features[f"{category}_250m"]).all(), (
            f"{category} buffer counts are not nested"
        )
        for suffix in ("inside", "250m", "500m"):
            counts = features[f"{category}_{suffix}"]
            assert (counts == np.floor(counts)).all(), "Non-integer destination count"


def compare_baseline(features):
    baseline = pd.read_csv(BASELINE / "sydney_hex_features.csv")
    baseline = baseline.set_index("hex_id").sort_index()
    current = features.drop(columns="geometry")
    current = current.set_index("hex_id").sort_index()
    # Includes the already corrected park distances, not the historical v4 values.
    pd.testing.assert_frame_equal(
        current, baseline, check_dtype=False, check_exact=False,
        rtol=1e-10, atol=TOLERANCE,
    )
    largest_difference = (current - baseline).abs().to_numpy().max()
    print(f"Baseline matches all columns; maximum difference: {largest_difference:.3g}")


def validate_exports():
    study_path = INTERIM / "boundaries/sydney_study_sa1_final.geojson"
    study = gpd.read_file(study_path)
    approved_path = REFERENCE / "approved_final_sa1_ids.txt"
    approved_ids = set(approved_path.read_text().splitlines())
    assert len(study) == 10503, "Expected 10,503 study SA1s"
    assert study["sa1_code"].is_unique, "Duplicate study SA1s"
    assert set(study["sa1_code"]) == approved_ids, "Approved SA1 membership changed"
    assert study.crs.to_epsg() == 7856, "Study geometry must use EPSG:7856"

    features = gpd.read_file(PROCESSED / "sydney_hex_features.gpkg")
    validate_features(features)
    compare_baseline(features)
    expected = features.drop(columns="geometry").set_index("hex_id").sort_index()
    csv = pd.read_csv(PROCESSED / "sydney_hex_features.csv")
    csv = csv.set_index("hex_id").sort_index()
    pd.testing.assert_frame_equal(
        csv, expected, check_dtype=False, rtol=1e-10, atol=TOLERANCE
    )

    geojson = gpd.read_file(PROCESSED / "sydney_hex_features.geojson")
    assert geojson.crs.to_epsg() == 4326, "GeoJSON must use EPSG:4326"
    attributes = geojson.drop(columns="geometry").set_index("hex_id").sort_index()
    pd.testing.assert_frame_equal(
        attributes, expected, check_dtype=False, rtol=1e-10, atol=TOLERANCE
    )
    geometry = geojson.to_crs(7856).set_index("hex_id").sort_index().geometry
    original = features.set_index("hex_id").sort_index().geometry
    assert (geometry.hausdorff_distance(original, align=False) < 1e-5).all(), (
        "GeoJSON geometry differs from the GeoPackage"
    )
    print("Validation passed: membership, counts, features, CRS and exports")
