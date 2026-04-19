#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AUDIT_ROOT = ROOT / "_audit" / "Nitrogen-Surplus-restructuring"
BOUNDARY_FILE = ROOT / "_audit" / "external" / "indian-district-boundaries" / "shapefile" / "india-districts-2019-734.shp"
DEFAULT_PYTHON = ROOT / ".venv" / "bin" / "python"
AUDIT_DEFAULT_PYTHON = AUDIT_ROOT / ".venv" / "bin" / "python"


def main() -> int:
    python_bin = os.environ.get("PYTHON_BIN")
    if not python_bin:
        if DEFAULT_PYTHON.exists():
            python_bin = str(DEFAULT_PYTHON)
        elif AUDIT_DEFAULT_PYTHON.exists():
            python_bin = str(AUDIT_DEFAULT_PYTHON)
        else:
            python_bin = sys.executable
    env = os.environ.copy()
    env.setdefault("MPLBACKEND", "Agg")

    subprocess.run([python_bin, "-m", "repro", "trade-stage"], cwd=AUDIT_ROOT, env=env, check=True)
    subprocess.run(
        [python_bin, "-m", "repro", "figure1", "--boundary-file", str(BOUNDARY_FILE)],
        cwd=AUDIT_ROOT,
        env=env,
        check=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
