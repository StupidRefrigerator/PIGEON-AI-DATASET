#!/usr/bin/env python3
"""Run the checked-out source from any working directory."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from urbangap.pipeline import run

if __name__ == "__main__":
    run()
