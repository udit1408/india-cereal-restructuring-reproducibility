#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
DEFAULT_PYTHON="$ROOT/.venv/bin/python"
PYTHON_BIN="${PYTHON_BIN:-}"
if [[ -z "$PYTHON_BIN" ]]; then
  if [[ -x "$DEFAULT_PYTHON" ]]; then
    PYTHON_BIN="$DEFAULT_PYTHON"
  else
    PYTHON_BIN="python3"
  fi
fi
BOUNDARY_FILE="$ROOT/_audit/external/indian-district-boundaries/shapefile/india-districts-2019-734.shp"

export MPLBACKEND=Agg

cd "$ROOT/_audit/Nitrogen-Surplus-restructuring"
"$PYTHON_BIN" -m repro trade-stage
"$PYTHON_BIN" -m repro figure1 --boundary-file "$BOUNDARY_FILE"
