# Completed validation

The refactored full pipeline passed in the original project environment and again in a newly created virtual environment installed solely from `requirements-lock.txt` plus the project package. `pip check` found no broken requirements. The final CSV is **byte-for-byte identical across both runs**. Exact hashes and the clean-environment record are in `reports/validation/`.

| Check | Result |
|---|---|
| Immutable original raw sources | All 153 checksums unchanged |
| Original raw files plus archived notebook/processed snapshots | All 181 pre-edit manifest entries verified |
| Final SA1 membership | Exact approved 10,503 IDs |
| H3 membership | Exact approved 16,228 IDs; no duplicates |
| Toilet placement | Exact 2,570 facilities across 1,911 occupied cells |
| Final schema | Identifier + placement proxy + 20 predictors; geometry in spatial exports |
| Missing, non-finite or negative features | None |
| Population nesting / density denominator | Passed |
| Park footprint bounds and nesting | Passed |
| Count integrality and buffer nesting | Passed |
| Rebuilt OSM extract objects | Exact canonical-object matches to both preserved PBFs |
| CSV / GeoPackage / GeoJSON | Consistent attributes, valid equivalent geometry; correct CRSs |
| All five active notebooks | Passed independently in fresh kernels; source outputs left empty |

## Feature comparison with v4

Comparison is by `hex_id`, never row position. Every retained numeric attribute is reported in `reports/validation/feature_comparison.csv` with changed count and maximum difference. Absolute tolerance is `1e-6`, relative tolerance `1e-10`.

- All 12 shop/food/bus/station count columns and `toilet_count` match **exactly**.
- `population_est`, `population_density`, `population_250m`, and `population_500m` match within floating-point noise; maximum difference across them is about `3.64e-12`.
- All three park footprint-area columns match within floating-point noise; maximum difference is about `5.82e-11 m²`. Their method was preserved.
- Only `distance_nearest_park_m` changes substantively: **110 cells**, maximum reduction **2,190.052315 m**, because the spatial index now queries all 6,998 available park polygons instead of the restricted 6,493-polygon context set. Old/new values are preserved for each affected cell.
- Historical `park_250m` and `park_500m` representative-point counts are intentionally excluded from the final schema and remain archived.

## Coverage and remaining limits

All 16,228 centroids are inside the reconstructed OSM extraction box. Every nearest available park distance is shorter than that centroid's distance to the box edge, with a minimum margin of approximately **4,982.12 m**. This reduces geographic edge concerns but does not prove complete OSM mapping or complete relation extraction. The feature remains distance to the nearest **available extracted mapped park**.

The historical density conflict is resolved through explicit frozen geographic membership, not an unsupported claim of a 500-based automatic reconstruction. See `methodology.md` and `reports/validation/study_history.json`.

The project is ready for ML feature/target experimentation within the documented study geography and placement-proxy interpretation. No training was performed. It is not evidence that an individual low-provision location has unmet demand; that inference needs later modeling and domain validation.
