# UrbanGap — Project Context

## Project objective

UrbanGap is a COMP3110 Machine Learning Engineering project at UNSW.

The initial goal is to identify potential gaps in public toilet provision in established urban areas of Greater Sydney, using geographic, demographic and OpenStreetMap features.

Existing toilet locations are used as an imperfect proxy for infrastructure placement, not as ground-truth evidence of unmet need.

## Geographic scope

- Greater Sydney, Australia.
- Australian Bureau of Statistics geographic boundaries.
- Focus on established urban areas.
- Exclude rural areas and selected growth corridors.
- Final study area: 10,503 SA1 polygons.
- H3 resolution 9 grid: 16,228 hexagons.
- Use EPSG:7856 for metric area and distance calculations.

## Data sources

- National Public Toilet Map.
- ABS 2021 Census G01 population data.
- ABS 2021 SA1 boundaries.
- ABS 2026 Greater Sydney and suburb boundaries.
- OpenStreetMap NSW extract from Geofabrik.

## Existing features

- Toilet counts per hexagon.
- Estimated population inside each hexagon.
- Population density.
- Shop, food, bus stop and train station counts inside hexagons and within 250 m and 500 m of hexagon centres.
- Park polygon overlap area inside hexagons and within 250 m and 500 m.
- Distance to nearest mapped park.
- Population within 250 m and 500 m, implemented and validated against the preserved v4 baseline.

## Key methodological decisions

- Use area-weighted population allocation from SA1 polygons.
- Use complete original SA1 areas as denominators.
- Include contextual features outside the final study boundary when within the relevant buffer.
- Exclude OSM shops tagged `shop=vacant`.
- Preserve legitimate OSM features even when multiple objects have similar names.
- Use park polygon area rather than park representative-point counts.
- Commercial polygon area features were considered but deferred.
- Use GeoPandas and Matplotlib for geographic analysis.
- Avoid assuming an existing public toilet necessarily indicates optimal placement.

## Important existing files

- `data/interim/boundaries/sydney_study_sa1_final.geojson` — Reconstructed approved SA1 study area.
- `data/interim/grid/sydney_hex_grid.geojson` — H3 grid and toilet counts.
- `data/interim/population/sa1_population_2021.csv` — Processed SA1 population.
- `data/processed/sydney_hex_features.gpkg` — Authoritative complete features in EPSG:7856.
- `data/processed/sydney_hex_features.csv` — Equivalent model-table attributes.
- `archive/baseline/data/processed/sydney_hex_features_v4.csv` — Preserved pre-cleanup regression reference.
- `data/raw/abs_sa1_2021/` — Original ABS SA1 shapefile.
- `data/raw/census_2021/` — Original Census population data.
- `data/raw/osm/` — OSM extracts.

## Reproducibility requirements

The cleaned project should have a documented, reproducible sequence from raw data to model-ready features.

Do not change the geographic study area, feature definitions or population allocation methodology without explicit approval.

Preserve existing data and notebooks until replacement outputs have been validated.

## Cleanup implementation (2026-10-21)

- The reproducible entry point is `python scripts/run_pipeline.py`; see `README.md` for environment setup.
- Authoritative outputs are `data/processed/sydney_hex_features.csv`, `.gpkg` and `.geojson`, with an explicit `feature_schema.json`.
- Historical notebooks and feature versions are preserved under `archive/`; originals are no longer production dependencies except the preserved regression-reference CSV and its manifest.
- Final geographic membership remains exactly 10,503 SA1s and 16,228 hexagons.
- Historical reconstruction showed that the saved preliminary selection reproduced at density **50**, contrary to the earlier inference that 500 generated it. The active urban-core threshold is **500**, while the approved geography is preserved by a versioned preliminary SA1 selection registry plus the original spatial growth exclusions. See `docs/methodology.md`; the pipeline does not claim a new 500-based clustering recipe produces the same region.
- Nearest-park distance uses all available extracted park polygons; 110 distances are corrected. Existing union-based park footprint areas are unchanged within numerical precision.
- Legacy park representative-point counts are archived and excluded from the final 20-predictor schema. No ML model or new target was introduced.
- Validation reports and per-feature baseline comparisons are in `reports/validation/`.
