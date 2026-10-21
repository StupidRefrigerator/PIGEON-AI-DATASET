import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely import area, buffer

from .common import ROOT, BASELINE, CRS, REPORTS, read_ids, require, sha256, write_json

LEGACY = ["park_250m", "park_500m"]
FEATURES = ["population_est", "population_density",
            *[f"{category}_{suffix}" for category in ("shop", "food", "bus_stop", "train_station")
              for suffix in ("inside", "250m", "500m")],
            "park_area_inside_m2", "park_area_250m_m2", "park_area_500m_m2",
            "distance_nearest_park_m", "population_250m", "population_500m"]
COLUMNS = ["hex_id", "toilet_count", *FEATURES, "geometry"]
ATOL = 1e-6
RTOL = 1e-10


def verify_raw():
    manifest = json.loads((ROOT / "docs/raw_manifest.json").read_text())
    for entry in manifest:
        path = ROOT / entry["path"]
        require(path.is_file() and sha256(path) == entry["sha256"], f"Raw source changed or missing: {path}")
    return {"verified_raw_files": len(manifest), "all_checksums_match": True}


def validate_features(frame):
    require(list(frame.columns) == COLUMNS, "Unexpected final schema")
    require(frame.crs.to_epsg() == 7856, "Final computation CRS must be EPSG:7856")
    require(len(frame) == 16228 and frame.hex_id.is_unique, "Wrong/duplicate hexagon IDs")
    require(set(frame.hex_id) == read_ids(ROOT / "docs/approved_hex_ids.txt"), "Grid membership changed")
    require(frame.geometry.notna().all() and frame.is_valid.all() and not frame.is_empty.any(), "Invalid hexagons")
    numeric = frame.drop(columns=["hex_id", "geometry"])
    require(np.isfinite(numeric.to_numpy()).all(), "Missing/infinite features")
    require((numeric >= 0).all().all(), "Negative features")
    require(frame.toilet_count.sum() == 2570 and (frame.toilet_count > 0).sum() == 1911,
            "Toilet placement baseline changed")
    require((frame.population_500m + ATOL >= frame.population_250m).all(), "Population buffers not nested")
    require((frame.population_250m + ATOL >= frame.population_est).all(), "Hex population exceeds containing buffer")
    require(np.allclose(frame.population_density, frame.population_est / (frame.area / 1e6), atol=ATOL, rtol=RTOL),
            "Population density denominator mismatch")
    require((frame.park_area_inside_m2 <= frame.area + ATOL).all(), "Impossible park area inside hex")
    for radius in (250, 500):
        maximum = area(buffer(frame.centroid.array, radius))
        require((frame[f"park_area_{radius}m_m2"] <= maximum + ATOL).all(), "Impossible buffer park area")
    require((frame.park_area_500m_m2 + ATOL >= frame.park_area_250m_m2).all(), "Park buffers not nested")
    require((frame.park_area_250m_m2 + ATOL >= frame.park_area_inside_m2).all(), "Park hex/buffer containment failed")
    for category in ("shop", "food", "bus_stop", "train_station"):
        require((frame[f"{category}_500m"] >= frame[f"{category}_250m"]).all(), "Counts not nested")
        for suffix in ("inside", "250m", "500m"):
            values = frame[f"{category}_{suffix}"]
            require((values == np.floor(values)).all(), "Non-integer OSM count")


def compare_baseline(frame):
    path = BASELINE / "data/processed/sydney_hex_features_v4.csv"
    require(path.is_file(), "Preserved baseline CSV required for regression validation; see README")
    manifest = json.loads((BASELINE / "file_manifest.json").read_text())
    expected = next(e["sha256"] for e in manifest if e["path"] == "data/processed/sydney_hex_features_v4.csv")
    require(sha256(path) == expected, "Preserved baseline CSV was modified")
    baseline = pd.read_csv(path).set_index("hex_id").sort_index()
    current = frame.drop(columns="geometry").set_index("hex_id").sort_index()
    require(set(baseline.index) == set(current.index), "Cannot compare different hexagon memberships")
    changes = []
    for column in current.columns:
        old, new = baseline[column].to_numpy(), current[column].to_numpy()
        changed = ~np.isclose(old, new, atol=ATOL, rtol=RTOL)
        delta = new - old
        record = {"column": column, "changed_hexagons": int(changed.sum()),
                  "max_absolute_difference": float(np.abs(delta).max()),
                  "reason": "all available parks replace the restricted 500 m park subset"
                  if column == "distance_nearest_park_m" else "unchanged within numerical tolerance"}
        changes.append(record)
        if column == "distance_nearest_park_m":
            require((delta <= ATOL).all(), "Expanded nearest-park search increased distances")
            require(changed.sum() == 110, "Nearest-park correction differs from independently audited 110 hexagons")
            comparison = pd.DataFrame({"hex_id": current.index[changed], "old_distance_m": old[changed],
                                       "new_distance_m": new[changed], "change_m": delta[changed]})
            comparison.to_csv(REPORTS / "nearest_park_corrections.csv", index=False)
        else:
            require(not changed.any(), f"Unapproved feature change: {record}")
    pd.DataFrame(changes).to_csv(REPORTS / "feature_comparison.csv", index=False)
    return {"absolute_tolerance": ATOL, "relative_tolerance": RTOL,
            "removed_legacy_columns": LEGACY, "comparisons": changes}


def validate_exports(frame, directory):
    directory = Path(directory)
    csv = pd.read_csv(directory / "sydney_hex_features.csv").set_index("hex_id").sort_index()
    expected = frame.drop(columns="geometry").set_index("hex_id").sort_index()
    require(list(csv.columns) == list(expected.columns) and csv.index.equals(expected.index), "CSV schema/IDs differ")
    require(np.allclose(csv.to_numpy(), expected.to_numpy(), atol=ATOL, rtol=RTOL), "CSV values differ")
    for suffix, crs in [("gpkg", 7856), ("geojson", 4326)]:
        geo = gpd.read_file(directory / f"sydney_hex_features.{suffix}")
        require(geo.crs.to_epsg() == crs, f"Wrong {suffix} CRS")
        attributes = geo.drop(columns="geometry").set_index("hex_id").sort_index()
        require(attributes.index.equals(expected.index) and list(attributes.columns) == list(expected.columns),
                f"{suffix} schema/IDs differ")
        require(np.allclose(attributes.to_numpy(), expected.to_numpy(), atol=ATOL, rtol=RTOL), f"{suffix} attributes differ")
        require(geo.is_valid.all() and not geo.is_empty.any(), f"Invalid exported {suffix} geometry")
        reconstructed = geo.to_crs(CRS).set_index("hex_id").sort_index().geometry
        original = frame.set_index("hex_id").sort_index().geometry
        require((reconstructed.hausdorff_distance(original, align=False) < 1e-5).all(), f"{suffix} geometry differs")
