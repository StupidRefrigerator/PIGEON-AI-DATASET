#!/usr/bin/env python3
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from pigeon_ai.geography import (
    add_toilet_counts,
    build_grid,
    build_study_area,
    load_population_boundaries,
)
from pigeon_ai.osm import add_osm_counts, add_park_features, load_osm, prepare_osm
from pigeon_ai.paths import INTERIM, PROCESSED
from pigeon_ai.population import add_population_buffers, add_population_features
from pigeon_ai.validation import COLUMNS, compare_baseline, validate_features


def main():
    print("1/7 Load Census population and build the approved study area", flush=True)
    boundaries = load_population_boundaries()
    study = build_study_area(boundaries)
    study_folder = INTERIM / "boundaries"
    study_folder.mkdir(parents=True, exist_ok=True)
    study.to_file(study_folder / "sydney_study_sa1_final.geojson", driver="GeoJSON")

    print("2/7 Generate H3 hexagons and count toilets", flush=True)
    grid = build_grid(study)
    grid = add_toilet_counts(grid)

    print("3/7 Allocate population to hexagons", flush=True)
    grid = add_population_features(grid, boundaries)

    print("4/7 Extract and load OSM destinations and parks", flush=True)
    osm_path = prepare_osm()
    objects, parks = load_osm(osm_path)

    print("5/7 Calculate destination counts and park features", flush=True)
    grid = add_osm_counts(grid, objects)
    grid = add_park_features(grid, parks)

    print("6/7 Allocate population within 250 m and 500 m", flush=True)
    grid = add_population_buffers(grid, boundaries)
    features = grid[COLUMNS].sort_values("hex_id").reset_index(drop=True)
    validate_features(features)
    compare_baseline(features)

    print("7/7 Save final CSV, GeoPackage and GeoJSON", flush=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    features.drop(columns="geometry").to_csv(
        PROCESSED / "sydney_hex_features.csv", index=False
    )
    features.to_file(
        PROCESSED / "sydney_hex_features.gpkg", layer="hex_features", driver="GPKG"
    )
    features.to_crs(4326).to_file(
        PROCESSED / "sydney_hex_features.geojson", driver="GeoJSON"
    )
    print(f"Saved {len(features):,} hexagons to {PROCESSED}", flush=True)

if __name__ == "__main__":
    main()
