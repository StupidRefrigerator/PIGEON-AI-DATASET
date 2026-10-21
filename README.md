# UrbanGap

UrbanGap builds geographic, demographic and OpenStreetMap features to investigate potential gaps in public-toilet provision across established urban Greater Sydney. Existing toilets are a proxy for historical infrastructure placement, not ground truth for unmet need. No model training is included.

The approved study area contains **10,503 SA1s** and **16,228 H3 resolution-9 cells**, containing **2,570 mapped toilet facilities in 1,911 cells**.

## Setup

Tested with Python **3.14.3**, osmium **1.19.1** (libosmium 2.23.1), and GDAL command-line tools **3.13.3** on macOS. GeoPandas uses the pinned Python geospatial stack; the GDAL CLI is separately required for OSM conversion. On macOS, native tools can be installed with `brew install osmium-tool gdal`. Native tool changes must pass the object and feature comparisons.

From the project root:

```sh
python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
python -m pip install --no-deps -e '.[notebooks]'
python scripts/run_pipeline.py
python scripts/validate_outputs.py
python scripts/check_notebooks.py
```

The pipeline runs in a fresh Python process, rebuilds OSM from the NSW PBF, and checks all raw checksums before and after processing. It does not need internet access after dependencies are installed. It writes a candidate first and publishes only after validation. Expect a few minutes of polygon intersection work.

Sources are not downloaded automatically. Keep the original source files at their paths in `docs/raw_manifest.json`. The preserved regression reference at `archive/baseline/data/processed/sydney_hex_features_v4.csv`, its `file_manifest.json`, and original notebooks must accompany this working project. Raw data and the full historical archive are intentionally ignored by Git; a code-only clone needs those data supplied separately. `docs/approved_*_ids.txt` are versioned geographic decision/validation inputs, not raw source substitutes.

For notebook exploration, start `jupyter lab` after running the pipeline. Active notebooks read outputs, explain assumptions and show diagnostics; they do not write feature datasets. Each is independently executable with a clean kernel. `scripts/check_notebooks.py` executes all five without saving bulky outputs to the source notebooks.

## Authoritative dataset

- `data/processed/sydney_hex_features.csv`: model-table export, one row per hexagon.
- `data/processed/sydney_hex_features.gpkg`: equivalent attributes and metric EPSG:7856 geometry; layer `hex_features`.
- `data/processed/sydney_hex_features.geojson`: equivalent attributes with EPSG:4326 geometry for interoperable mapping.
- `data/processed/feature_schema.json`: explicit identifier, placement proxy and model feature list.

The final table has 20 predictors, `hex_id`, and `toilet_count`. Geometry is available in the geospatial exports. The old representative-point park counts are excluded; park footprint areas and nearest mapped-park distance are retained. See [data dictionary](docs/data_dictionary.md).

## Project structure

```text
data/raw/                 immutable original sources, including preserved PBFs
data/interim/             reproducible population, study area, grid, OSM and candidate outputs
data/processed/           authoritative feature exports and schema
src/urbangap/             shared preparation, feature calculation and validation
scripts/                  pipeline, output validation and notebook execution
notebooks/                five independent explanatory notebooks
docs/                     methodology, provenance, dictionary and approved geographic registries
reports/validation/       baseline comparisons, corrections and validation summaries
archive/baseline/         untouched initial snapshot, IDs, statistics and checksums
archive/legacy_processed/ historical processed directory, including DuckDB and WAL together
archive/exploration_artifacts/ historical map and geocoding cache
```

## Reproduction and important findings

The pipeline extracts G01 population; reconstructs approved SA1 geography and growth exclusions; generates H3 cells; assigns national toilet records; allocates population using complete original SA1 areas; reconstructs and converts OSM; calculates active-shop/food/transport counts; reproduces union-based park areas; corrects nearest-park distances using all available park polygons; and allocates contextual buffer population.

The cleanup discovered that the historical preliminary membership reproduces at density **50**, despite saved counts/titles suggesting **500**. The active urban-core threshold is now 500. To preserve the approved boundary, production uses an explicit preliminary SA1 selection registry followed by the original spatial growth-suburb exclusions. It does **not** claim that a new 500-based cluster recipe independently recreates the old boundary. See [methodology](docs/methodology.md) and [migration record](docs/migration_report.md).

OSM extraction/conversion commands were reconstructed and validated against preserved objects; their historical command history was not recovered. The NSW PBF records a replication timestamp of `2026-10-18T20:25:06Z`. Nearest-park distances are correct among available extracted park polygons, not guaranteed across incomplete OSM mapping or omitted relations. See [provenance](docs/data_provenance.md).

## Validation evidence

`reports/validation/validation.json` records a successful run, source integrity, environment, exact membership and totals, and export hashes. `feature_comparison.csv` reports every retained attribute against v4 by `hex_id`; `nearest_park_corrections.csv` preserves old/new distances for every corrected cell. Numerical comparisons use absolute tolerance `1e-6` and relative tolerance `1e-10`; count changes are not expected. All original park-area features are preserved.

See [completed validation results](docs/validation_results.md) for the full checklist. The pipeline also passed in a newly installed virtual environment and reproduced the same CSV byte-for-byte.

For ML work, use only the `model_features` list from the schema. Keep `hex_id` and geometry out of predictors; choose a target formulation explicitly using the placement proxy. Spatial evaluation and interpretation of apparent provision gaps remain modeling work, not part of this cleanup.
