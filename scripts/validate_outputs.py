#!/usr/bin/env python3
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from pigeon_ai.validation import validate_exports

if __name__ == "__main__":
    validate_exports()
