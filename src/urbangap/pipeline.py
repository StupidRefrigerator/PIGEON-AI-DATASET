"""A fresh-process, raw-to-export pipeline. Never writes to raw/ or the baseline."""
import json
import platform
from importlib.metadata import version

from .common import ROOT, INTERIM, PROCESSED, REPORTS, export_pair, sha256, write_json
from .study import prepare_population, load_sa1, build_study
from .grid import build_grid, assign_toilets
from .population import add_population_features, add_population_buffers
from .osm import prepare_osm, load_objects, add_count_features, add_park_features
from .validation import COLUMNS, FEATURES, validate_features, compare_baseline, validate_exports, verify_raw


def run():
    REPORTS.mkdir(parents=True, exist_ok=True)
    print("1/10 Verify immutable raw sources", flush=True)
    raw = verify_raw()
    print("2/10 Prepare Census population and approved study geography", flush=True)
    population = prepare_population()
    sa1 = load_sa1(population)
    preliminary, study, study_report = build_study(sa1)
    boundary_dir = INTERIM / "boundaries"
    boundary_dir.mkdir(parents=True, exist_ok=True)
    preliminary.to_file(boundary_dir / "sydney_study_sa1_preliminary.geojson", driver="GeoJSON")
    study.to_file(boundary_dir / "sydney_study_sa1_final.geojson", driver="GeoJSON")
    print("3/10 Generate approved H3 grid and assign national toilet records", flush=True)
    grid, toilets_report = assign_toilets(build_grid(study))
    export_pair(grid, INTERIM / "grid", "sydney_hex_grid")
    print("4/10 Allocate population to complete hexagons", flush=True)
    grid = add_population_features(grid, sa1)
    print("5/10 Reconstruct OSM extracts and convert to GeoPackage", flush=True)
    path = prepare_osm()
    objects, parks = load_objects(path)
    print("6/10 Count shop, food, bus and rail objects", flush=True)
    grid, osm_report = add_count_features(grid, objects)
    print("7/10 Reproduce park footprint areas and correct nearest distances", flush=True)
    grid, coverage_report = add_park_features(grid, parks)
    print("8/10 Allocate population within centre buffers", flush=True)
    grid, population_report = add_population_buffers(grid, sa1)
    grid = grid[COLUMNS].sort_values("hex_id").reset_index(drop=True)
    print("9/10 Validate all features against preserved baseline", flush=True)
    validate_features(grid)
    comparison = compare_baseline(grid)
    # Write a candidate, then validate its serialized exports before publication.
    candidate = INTERIM / "validated_candidate"
    export_pair(grid, candidate, "sydney_hex_features")
    grid.to_file(candidate / "sydney_hex_features.gpkg", layer="hex_features", driver="GPKG")
    grid.to_crs(4326).to_file(candidate / "sydney_hex_features.geojson", driver="GeoJSON")
    validate_exports(grid, candidate)
    verify_raw()
    print("10/10 Publish validated feature exports", flush=True)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    import shutil
    for source in candidate.glob("sydney_hex_features.*"):
        shutil.copy2(source, PROCESSED / source.name)
    exports = {p.name: sha256(p) for p in sorted(PROCESSED.glob("sydney_hex_features.*"))}
    source_files = [*sorted((ROOT / "src/urbangap").glob("*.py")),
                    *sorted((ROOT / "scripts").glob("*.py")),
                    *sorted((ROOT / "docs").glob("approved_*_ids.txt")),
                    ROOT / "docs/study_selection.json", ROOT / "requirements-lock.txt", ROOT / "pyproject.toml"]
    report = {"status": "passed", "rows": len(grid), "study_area": study_report, "toilets": toilets_report,
              "raw_sources": raw, "osm_counts": osm_report, "park_coverage": coverage_report,
              "population_context": population_report, "baseline_comparison": comparison,
              "exports_sha256": exports, "python": platform.python_version(),
              "source_sha256": {str(p.relative_to(ROOT)): sha256(p) for p in source_files},
              "packages": {name: version(name) for name in ("geopandas", "shapely", "pandas", "numpy", "h3", "pyogrio", "pyproj")}}
    write_json(REPORTS / "validation.json", report)
    write_json(PROCESSED / "feature_schema.json", {"identifier": "hex_id", "placement_proxy": "toilet_count",
               "model_features": FEATURES, "geometry": {"gpkg_crs": "EPSG:7856", "geojson_crs": "EPSG:4326"}})
    print(f"PASS: {len(grid):,} hexagons; validated exports in {PROCESSED}", flush=True)
    return report
