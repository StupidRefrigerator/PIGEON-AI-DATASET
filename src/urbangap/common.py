from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data/raw"
INTERIM = ROOT / "data/interim"
PROCESSED = ROOT / "data/processed"
BASELINE = ROOT / "archive/baseline"
REPORTS = ROOT / "reports/validation"
CRS = "EPSG:7856"
RESOLUTION = 9
RADII = (250, 500)


def require(condition, message):
    """Validation remains active even when Python is invoked with -O."""
    if not condition:
        raise ValueError(message)


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def read_ids(path):
    return set(Path(path).read_text().splitlines())


def export_pair(frame, directory, name):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    frame = frame.sort_values("hex_id").reset_index(drop=True)
    frame.to_file(directory / f"{name}.geojson", driver="GeoJSON")
    frame.drop(columns="geometry").to_csv(directory / f"{name}.csv", index=False)
