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

"$PYTHON_BIN" "$ROOT/scripts/generate_si_figure2_supporting_block.py"
"$PYTHON_BIN" "$ROOT/scripts/generate_seasonal_substitution_audit.py"
"$PYTHON_BIN" "$ROOT/scripts/generate_si_revenue_robustness_figure.py"
"$PYTHON_BIN" "$ROOT/scripts/generate_si_revenue_benchmark_endpoint_sensitivity.py"
"$PYTHON_BIN" "$ROOT/scripts/generate_si_revenue_profit_sensitivity.py"
"$PYTHON_BIN" "$ROOT/scripts/generate_si_figure2a_frontier_bootstrap.py"
"$PYTHON_BIN" "$ROOT/scripts/build_source_data_package.py"
"$PYTHON_BIN" "$ROOT/scripts/generate_audited_html_report.py"
