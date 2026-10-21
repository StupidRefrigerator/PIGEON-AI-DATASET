# Authoritative feature data dictionary

Files: `data/processed/sydney_hex_features.csv`, `.gpkg` (layer `hex_features`), and `.geojson`. One row per approved complete H3 resolution-9 cell: **16,228 rows, 22 tabular columns**. The 20 model predictors are explicitly listed in `feature_schema.json`. No transformed target, gap score or model prediction has been added.

The CSV has no geometry. GeoPackage geometry is EPSG:7856; GeoJSON geometry is EPSG:4326. Metric calculations are performed in EPSG:7856 before either export. `inside` always refers to the complete hexagon, not its intersection with the SA1 study region. Buffer distances are measured from the projected hexagon centroid.

| Column | Role | Type / units | Definition and calculation |
|---|---|---|---|
| `hex_id` | Identifier | String | H3 resolution-9 cell ID; unique, never an ordinal predictor |
| `toilet_count` | Historical placement proxy / candidate target input | Nonnegative integer facilities | National Public Toilet Map records assigned by H3 coordinate lookup; zero-filled across the full grid. Not a count of cubicles or evidence of unmet demand |
| `population_est` | Model feature | Nonnegative float people | Sum of original SA1 populations multiplied by hexagon overlap fraction using complete original SA1 areas |
| `population_density` | Model feature | Nonnegative float people/km² | `population_est` divided by complete projected hexagon area in km² |
| `shop_inside` | Model feature | Nonnegative integer OSM objects | Shop-tagged points/polygon representatives strictly within the cell; excludes `shop=vacant` |
| `shop_250m` | Model feature | Nonnegative integer OSM objects | Active/known-type shop objects intersecting the 250 m centre buffer |
| `shop_500m` | Model feature | Nonnegative integer OSM objects | Active/known-type shop objects intersecting the 500 m centre buffer |
| `food_inside` | Model feature | Nonnegative integer OSM objects | `amenity=cafe` or `restaurant` objects strictly within the cell |
| `food_250m` | Model feature | Nonnegative integer OSM objects | Cafe/restaurant objects intersecting the 250 m centre buffer |
| `food_500m` | Model feature | Nonnegative integer OSM objects | Cafe/restaurant objects intersecting the 500 m centre buffer |
| `bus_stop_inside` | Model feature | Nonnegative integer OSM objects | `highway=bus_stop` objects strictly within the cell |
| `bus_stop_250m` | Model feature | Nonnegative integer OSM objects | Bus stop objects intersecting the 250 m centre buffer |
| `bus_stop_500m` | Model feature | Nonnegative integer OSM objects | Bus stop objects intersecting the 500 m centre buffer |
| `train_station_inside` | Model feature | Nonnegative integer OSM objects | `railway=station` objects strictly within the cell; counts OSM objects, not deduplicated station complexes |
| `train_station_250m` | Model feature | Nonnegative integer OSM objects | Station objects intersecting the 250 m centre buffer |
| `train_station_500m` | Model feature | Nonnegative integer OSM objects | Station objects intersecting the 500 m centre buffer |
| `park_area_inside_m2` | Model feature | Nonnegative float m² | Area of intersection between full cell and unioned contextual `leisure=park` polygons |
| `park_area_250m_m2` | Model feature | Nonnegative float m² | Unioned park footprint intersected with the 250 m centre buffer, using historical Shapely buffer approximation |
| `park_area_500m_m2` | Model feature | Nonnegative float m² | Unioned park footprint intersected with the 500 m centre buffer, using historical Shapely buffer approximation |
| `distance_nearest_park_m` | Model feature | Nonnegative float metres | Indexed minimum straight-line distance from projected centroid to any available extracted park polygon; zero inside a park. Corrected from v4's restricted candidate set |
| `population_250m` | Model feature | Nonnegative float people | Area-weighted original SA1 population in a 250 m centre buffer, including contextual SA1s outside the approved study area |
| `population_500m` | Model feature | Nonnegative float people | Same allocation in a 500 m centre buffer, using complete original SA1 denominators |
| `geometry` | Geographic attribute, geospatial exports only | Polygon | Complete H3 polygon, uncut by study boundary; not part of the predictor list |

## Interpretive rules

- Population estimates are fractional allocations, not observed counts at hexagon scale. Zeros are allowed; missing inputs are not silently treated as observed zero.
- A single OSM object may satisfy multiple categories. Distinct named or colocated objects are retained; no automatic name-based deduplication occurs.
- Polygon destinations use representative points in their source CRS before metric projection. Parks instead use original polygon footprints for area/distance.
- Counts and population buffers use GeoPandas's original circle approximation; park areas use Shapely's original approximation. These are documented, preserved definitions.
- Surrounding context can lie beyond the prediction region. Buffer populations/counts overlap between hexagons and are not regional totals.
- `toilet_count` is excluded from predictors. A later modeling project must explicitly choose count/presence formulation and interpretation; no binary target was added during cleanup.

## Historical fields excluded from the final table

| Field | Where preserved | Reason |
|---|---|---|
| `park_250m`, `park_500m` | Archived OSM/v2/v3/v4 exports | Counted park point/representative-point objects; superseded by polygon footprint definitions and excluded as requested |
| `area_km2` | Archived original population-feature export | Geographic denominator lost from later historical versions; reproducible from geometry, not an established v4 model feature |
| `hex_area_m2` | Original notebook diagnostic | Added after v3 was written; not part of the saved v4 dataset or a new predictor |

All other useful v4 columns remain. Original versions and their schemas are preserved in `archive/baseline/`; old park distances for each affected hexagon are in `reports/validation/nearest_park_corrections.csv`.
