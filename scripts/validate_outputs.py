#!/usr/bin/env python3
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import geopandas as gpd
from urbangap.common import PROCESSED, REPORTS
from urbangap.validation import validate_features, compare_baseline, validate_exports, verify_raw

if __name__ == "__main__":
    REPORTS.mkdir(parents=True, exist_ok=True)
    frame = gpd.read_file(PROCESSED / "sydney_hex_features.gpkg")
    verify_raw()
    validate_features(frame)
    compare_baseline(frame)
    validate_exports(frame, PROCESSED)
    print("PASS: raw checksums, membership, feature values and all exports")
