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

export MPLBACKEND=Agg
export PYTHONPATH="$ROOT/_audit/Nitrogen-Surplus-restructuring${PYTHONPATH:+:$PYTHONPATH}"

"$PYTHON_BIN" "$ROOT/scripts/generate_Figure3_equivalent.py" "$@"
