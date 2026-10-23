#!/usr/bin/env python3
from pathlib import Path
import argparse
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pigeon_ai.validation import validate_exports

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check-baseline",
        action="store_true",
        help="Require an exact match with the archived dataset in archive/",
    )
    validate_exports(parser.parse_args().check_baseline)
