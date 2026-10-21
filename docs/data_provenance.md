# Data provenance and reconstruction

## Source inventory

`raw_manifest.json` records the relative path, byte size and SHA-256 of every original raw file before refactoring. Raw files have not been moved or rewritten. Baseline checksums, row counts, schemas and numeric statistics are in `archive/baseline/file_manifest.json` and `dataset_summary.json`. Original notebooks and processed datasets were copied there before modification. The original processed directory was then archived as a unit at `archive/legacy_processed/`, preserving the DuckDB database and WAL together. Neither database was opened writable.

| Source | Local input | Available vintage/provenance | Important limits |
|---|---|---|---|
| National Public Toilet Map | `data/raw/national_toilets.csv` | 25,624 records; original export retained | Export/retrieval date and original download URL not recorded; facility inventory is an imperfect placement proxy |
| ABS Census G01 | `data/raw/census_2021/2021 Census GCP Statistical Area 1 for NSW/2021Census_G01_NSW_SA1.csv` | 2021 Census; 19,750 NSW SA1 records; `Tot_P_P` | Remaining 118 Census CSVs and package metadata are preserved but unused |
| ABS SA1 boundaries | `data/raw/abs_sa1_2021/SA1_2021_AUST_GDA2020.shp` and sidecars | 2021; source CRS EPSG:7844; 61,845 national records | Only NSW Census data supplied; non-NSW missing population is expected until contextual geographic selection |
| ABS Greater Capital City Statistical Areas | `data/raw/abs_boundaries/GCCSA_2026_AUST_GDA2020.shp` and sidecars | 2026; GDA2020 | Used for the original suburb selection, not to replace 2021 SA1 membership attributes |
| ABS suburbs/localities | `data/raw/abs_suburbs/SAL_2026_AUST_GDA2020.shp` and sidecars | 2026; GDA2020 | Growth exclusions use representative points, not clipping or any-overlap exclusion |
| Geofabrik NSW OSM extract | `data/raw/osm/nsw.osm.pbf` | PBF header: replication sequence 194, timestamp `2026-10-18T20:25:06Z`, generator osmium/1.16.0 | Header describes replication state, not proof of original retrieval time |
| Preserved Sydney extracts | `data/raw/osm/sydney.osm.pbf`, `sydney_pois.osm.pbf` | Headers identify osmium/1.19.1; no retained snapshot timestamp | Derived sources already placed under raw before cleanup; retained immutable |

The NSW header records replication base URL `https://download.geofabrik.de/australia-oceania/australia/new-south-wales-updates`. Original download commands and retrieval logs were not present. Source-specific ABS licensing/readme/metadata files remain alongside the data; consult them before redistribution. The archived OSM cache includes its original ODbL attribution. OSM-derived exports require appropriate OpenStreetMap attribution when used or shared.

## Reconstructed OSM commands

The following commands were reconstructed from preserved contents, not recovered from shell history. Run from the project root after creating `data/interim/osm/`:

```sh
osmium extract -b 150.45,-34.25,151.40,-33.35 -s complete_ways \
  data/raw/osm/nsw.osm.pbf -o data/interim/osm/sydney.osm.pbf --overwrite
osmium tags-filter data/interim/osm/sydney.osm.pbf \
  nwr/shop nwr/amenity=cafe,restaurant nwr/highway=bus_stop \
  nwr/railway=station nwr/leisure=park \
  -o data/interim/osm/sydney_pois.osm.pbf --overwrite
ogr2ogr -f GPKG -overwrite data/interim/osm/sydney_pois.gpkg \
  data/interim/osm/sydney_pois.osm.pbf
```

Osmium retains referenced objects by default; `--omit-referenced` and `--remove-tags` are deliberately absent. The converter uses GDAL's default OSM layer/configuration behavior in the tested installation. A different default configuration is not assumed equivalent: baseline feature comparison must pass.

`osmium cat FILE -f opl` produces the canonical object representation used for comparison. Rebuilt and preserved extracts match exactly under this representation:

| Extract | Canonical OPL SHA-256 |
|---|---|
| Sydney | `fe228f19911c9d609115245637fa323bc3e23134add18c0c385eab50dfe93f5c` |
| POIs | `1a2873604c53c39863ebd63e5a7bcfbf78687440bbfa602f77724e7d4185db06` |

Converting the preserved POI PBF with the tested GDAL produced point and multipolygon layers identical to the original GeoPackage in columns, attributes, geometry and ordering: **42,741 points and 9,668 multipolygons**. The complete rebuild also validates final features, so the production pipeline does not depend on the historical GeoPackage. PBF file hashes may differ due to encoding/headers despite identical objects. Preparation commands, tool versions and object comparisons are written to `data/interim/osm/preparation.json`.

## Geographic coverage

The reconstructed extraction box covers the prediction grid and its 500 m context. Complete ways can extend outside it, as seen in polygon bounds; observed object bounds alone do not establish coverage. The pipeline reports centre-to-extraction-edge margins for nearest parks. `complete_ways` does not guarantee complete park relations at the extraction boundary, and OSM coverage is imperfect even inside the box. The corrected distance uses the complete available polygon layer without claiming globally complete parks.

## Processing lineage

```text
Census G01 → interim population table
raw SA1s + population + approved preliminary registry
  + 2026 Greater Sydney/suburbs + explicit growth list → final study SA1s
final study SA1 union → full H3 cells
national toilet CSV → H3 assignments → toilet_count
original SA1s + population + full cells → area-weighted hex population/density
NSW PBF → bbox extract → tagged/reference objects → GeoPackage
GeoPackage points/polygon representatives → shop/food/transit counts
GeoPackage original park polygons → union footprint areas + indexed nearest parks
original SA1s + population + centre buffers → contextual population
all feature stages → baseline/geometry/export validation → final exports
```

## Preserved historical versions

The baseline base-population, initial OSM, v2, v3 and v4 files remain available for investigation. Initial OSM features included vacant shops; v2 corrected shops and added inside counts; v3 added polygon park features while retaining legacy point counts; v4 added population buffers. The new final schema removes only `park_250m` and `park_500m`. Other feature changes are prohibited except the documented nearest-park correction.

The 3,166-record bounding-box toilet count file and later 3,355-record Greater Sydney toilet subset describe different selection branches. Neither is an input to the authoritative pipeline. The DuckDB exploration is likewise disconnected from the production GeoPackage chain.

## Unresolved history and explicit decisions

- The exact historical shell commands were absent; content-equivalent commands are now documented and verified.
- Original toilet/ABS retrieval dates and some URLs were absent; file names/metadata identify available vintages without inventing retrieval history.
- Contrary to the earlier audit inference and approval premise, the saved geographic selection reproduces at density 50. A versioned geographic selection registry now preserves the approved boundary, with density 500 documented separately as the urban-core threshold. See methodology and migration report.
- New versions of sources require deliberate manifest/selection review; this pipeline intentionally fails when supplied raw files differ from the approved snapshot.
