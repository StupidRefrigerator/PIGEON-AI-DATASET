#!/usr/bin/env python3
from pathlib import Path
import os
import sys
import tempfile

import nbformat
from jupyter_client import KernelManager
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parents[1]


if __name__ == "__main__":
    with tempfile.TemporaryDirectory(prefix="pigeon-ai-notebooks-") as temporary:
        os.environ["MPLCONFIGDIR"] = temporary
        os.environ["IPYTHONDIR"] = temporary
        for path in sorted((ROOT / "notebooks").glob("*.ipynb")):
            notebook = nbformat.read(path, as_version=4)
            manager = KernelManager(kernel_name="python3")
            manager.kernel_spec.argv = [
                sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"
            ]
            client = NotebookClient(
                notebook,
                km=manager,
                timeout=300,
                resources={"metadata": {"path": str(ROOT / "notebooks")}},
            )
            # An external manager needs explicit cleanup after each fresh kernel.
            try:
                client.execute()
            finally:
                if manager.has_kernel:
                    manager.shutdown_kernel(now=True)
            print("PASS:", path.name, flush=True)
