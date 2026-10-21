# Cleanup and migration record

Implementation date: 2026-10-21 (Australia/Sydney).

## Preserved before editing

`archive/baseline/` contains original notebooks, all original processed artifacts, sorted approved final SA1/H3 IDs, file checksums, CSV schemas, row counts and numeric statistics. Raw files were hashed, not rewritten. `archive/legacy_processed/` holds the original processed directory, moved as a unit including both DuckDB files. Original map/cache artifacts remain archived. No historical dataset or notebook was deleted.

## Geographic discrepancy investigated

The earlier audit correctly identified a mismatch between the density source code and saved output, but inferred that 500 produced the saved geography. Independent reconstruction disproved that inference:

| Density threshold | Retained Sydney SA1s | Union components | Result using old component positions | Difference from preliminary baseline |
|---|---:|---:|---:|---:|
| 50 | 11,612 | 68 | 10,753 SA1s | 0 IDs |
| 500 | 11,138 | 119 | 23 SA1s | 10,774 IDs in symmetric difference |

The approved requirements to preserve geography and claim an automatic 500-based reproduction cannot both be met by merely changing the constant. Production therefore sets 500 as the documented urban-core threshold but uses a transparent, explicit geographic membership registry for the approved preliminary selection. It reconstructs geometry from immutable raw boundaries and recalculates the original growth exclusions. Exact final membership is independently asserted. No positional component identifier remains in production.

This is a reproducible frozen geographic decision, not a new density-selection algorithm. An independently derived 500-density study-region definition would be a future methodological revision requiring boundary approval. It is not silently substituted here.

## Refactoring

- Replaced hidden notebook state with reusable population, study, H3, toilet, OSM and validation functions.
- Reconstructed raw-to-GeoPackage commands; verified canonical OSM objects and original GeoPackage layers.
- Replaced the restricted nearest-park universe with an indexed query over all available park polygons.
- Preserved original population denominators, park unions, point conversion order, predicates and buffer approximations.
- Removed legacy park representative-point columns from the final feature schema; preserved their historical values in the archive.
- Added candidate-first export validation, raw integrity checks, exact geographic/placement checks and comparisons by hexagon ID.
- Rewrote five notebooks as explanatory, independently executable inspections, preserving original versions.
- Added pinned dependencies, source/selection manifests, documentation, execution scripts and Git ignore rules. Git commits are left to the project owner; no raw/archive data are staged.

## Evidence

`reports/validation/validation.json` is the machine-readable full-run result. `feature_comparison.csv` covers every retained attribute, including unchanged columns and numerical differences. `nearest_park_corrections.csv` records every old/new distance and change. `notebook_execution.json` records fresh-kernel execution of active notebooks. Source/output checksums and environment metadata allow later runs to be compared.

The final dataset is appropriate for subsequent ML development with its documented placement-proxy interpretation. No model was trained and no prediction target was redefined. Spatial validation, temporal limitations, OSM completeness and actual unmet-demand inference remain modeling responsibilities.
