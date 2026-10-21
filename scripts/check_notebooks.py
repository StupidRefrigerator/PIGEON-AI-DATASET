#!/usr/bin/env python3
"""Execute each notebook in a fresh kernel, keeping bulky outputs out of source."""
from pathlib import Path
import os
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import nbformat
from nbclient import NotebookClient
from urbangap.common import ROOT, REPORTS, write_json


if __name__ == "__main__":
    results = []
    with tempfile.TemporaryDirectory(prefix="urbangap-notebooks-") as temporary:
        os.environ["MPLCONFIGDIR"] = temporary
        os.environ["IPYTHONDIR"] = temporary
        # Use this interpreter, not whichever 'python3' kernel happens to be registered.
        kernels = Path(temporary) / "kernels/urbangap"
        kernels.mkdir(parents=True)
        write_json(kernels / "kernel.json", {"argv": [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
                   "display_name": "UrbanGap validation", "language": "python"})
        os.environ["JUPYTER_PATH"] = temporary + os.pathsep + os.environ.get("JUPYTER_PATH", "")
        for path in sorted((ROOT / "notebooks").glob("*.ipynb")):
            notebook = nbformat.read(path, as_version=4)
            client = NotebookClient(notebook, timeout=300, kernel_name="urbangap",
                                    resources={"metadata": {"path": str(ROOT / "notebooks")}})
            client.execute()
            results.append({"notebook": path.name, "status": "passed", "cells": len(notebook.cells)})
            print("PASS:", path.name, flush=True)
    write_json(REPORTS / "notebook_execution.json", results)
