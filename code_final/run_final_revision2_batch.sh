#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEFAULT_PYTHON="$ROOT/.venv/bin/python"
PYTHON_BIN="${PYTHON_BIN:-}"
if [[ -z "$PYTHON_BIN" ]]; then
  if [[ -x "$DEFAULT_PYTHON" ]]; then
    PYTHON_BIN="$DEFAULT_PYTHON"
  else
    PYTHON_BIN="python3"
  fi
fi
MODE="full"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --report-only)
      MODE="report-only"
      shift
      ;;
    *)
      echo "Unknown argument: $1" >&2
      echo "Usage: $0 [--report-only]" >&2
      exit 2
      ;;
  esac
done

export MPLBACKEND=Agg
export PYTHONPATH="$ROOT/_audit/Nitrogen-Surplus-restructuring${PYTHONPATH:+:$PYTHONPATH}"

OUT_DIR="$ROOT/submission_assets/audited_html_report"
LOG_DIR="$OUT_DIR/logs"
mkdir -p "$LOG_DIR"

RUN_TIMESTAMP="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
RUN_STAMP="$(date -u +"%Y%m%dT%H%M%SZ")"
LOG_FILE="$LOG_DIR/public_repro_batch_${RUN_STAMP}.log"
LATEST_LOG="$LOG_DIR/latest_run.log"

exec > >(tee "$LOG_FILE") 2>&1
ln -sf "$(basename "$LOG_FILE")" "$LATEST_LOG"

BOUNDARY_FILE="$ROOT/_audit/external/indian-district-boundaries/shapefile/india-districts-2019-734.shp"
RUN_CONTEXT="$OUT_DIR/run_context.json"

run_step() {
  echo
  echo "==> $1"
  shift
  "$@"
}

write_run_context() {
  cat > "$RUN_CONTEXT" <<EOF
{
  "timestamp_utc": "$RUN_TIMESTAMP",
  "mode": "$MODE",
  "runner": "code_final/run_final_revision2_batch.sh",
  "manifest": "code_final/FINAL_CODE_MANIFEST.md",
  "method_notation_map": "code_final/METHOD_NOTATION_MAP.md",
  "log_file": "logs/$(basename "$LOG_FILE")"
}
EOF
}

echo "Audited reproducibility batch runner"
echo "root: $ROOT"
echo "python: $PYTHON_BIN"
echo "mode: $MODE"
echo "timestamp_utc: $RUN_TIMESTAMP"

mkdir -p "$OUT_DIR"
write_run_context

if [[ "$MODE" == "full" ]]; then
  run_step "Trade-stage normalization from audited checkout" \
    bash -lc "cd '$ROOT/_audit/Nitrogen-Surplus-restructuring' && '$PYTHON_BIN' -m repro trade-stage"

  run_step "Figure 1 audited reproduction" \
    bash -lc "cd '$ROOT/_audit/Nitrogen-Surplus-restructuring' && '$PYTHON_BIN' -m repro figure1 --boundary-file '$BOUNDARY_FILE'"

  run_step "Figure 2 primary realized-price rebuild" \
    "$PYTHON_BIN" "$ROOT/scripts/generate_figure2_main.py" --scenario-year 2017-18 --bootstrap-iterations 500 --bootstrap-seed 42

  run_step "Supplementary Figure 2 supporting block" \
    "$PYTHON_BIN" "$ROOT/scripts/generate_si_figure2_supporting_block.py"

  run_step "Figure 3 primary realized-price rebuild" \
    "$PYTHON_BIN" "$ROOT/scripts/generate_figure3_main.py"

  run_step "Seasonal substitution audit" \
    "$PYTHON_BIN" "$ROOT/scripts/generate_seasonal_substitution_audit.py"

  run_step "Revenue robustness SI figure" \
    "$PYTHON_BIN" "$ROOT/scripts/generate_si_revenue_robustness_figure.py"

  run_step "Revenue endpoint sensitivity SI figure" \
    "$PYTHON_BIN" "$ROOT/scripts/generate_si_revenue_benchmark_endpoint_sensitivity.py"

  run_step "Revenue-profit SI figure" \
    "$PYTHON_BIN" "$ROOT/scripts/generate_si_revenue_profit_sensitivity.py"

  run_step "Figure 2(a) envelope SI figure" \
    "$PYTHON_BIN" "$ROOT/scripts/generate_si_figure2a_frontier_bootstrap.py"

  run_step "Source Data package rebuild" \
    "$PYTHON_BIN" "$ROOT/scripts/build_source_data_package.py"

  run_step "Release-figure exact-match verification" \
    "$PYTHON_BIN" "$ROOT/scripts/verify_release_figures.py"
fi

run_step "HTML reproducibility report" \
  "$PYTHON_BIN" "$ROOT/scripts/generate_audited_html_report.py"

echo
echo "Audited reproducibility batch complete."
echo "HTML report: $ROOT/submission_assets/audited_html_report/index.html"
echo "Manifest:    $ROOT/submission_assets/audited_html_report/repro_manifest.json"
echo "Log:         $LOG_FILE"
