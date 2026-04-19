#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="$ROOT/_audit/Nitrogen-Surplus-restructuring/.venv/bin/python"

echo "Rebuilding approved Figure 2(a) assets under fixed district area and historically observed cereals..."
"$PYTHON" "$ROOT/scripts/export_figure2a_assets.py"

echo "Rebuilding approved Figure 2(b) endpoint panel under fixed district area and historically observed cereals..."
"$PYTHON" "$ROOT/scripts/generate_figure2b_clean.py" --no-historical-caps --output-stem figure2b_no_historical_cap_core

echo "Rebuilding approved Figure 2(b) district-input bootstrap summaries..."
"$PYTHON" "$ROOT/scripts/bootstrap_figure2b_no_historical_cap_core.py" --iterations 500 --seed 42

echo "Rebuilding approved Figure 2(b) all-metric bootstrap panel..."
"$PYTHON" "$ROOT/scripts/generate_figure2b_all_metric_bootstrap.py"

echo "Rebuilding approved Figure 2(b) primary-endpoint bootstrap panel..."
"$PYTHON" "$ROOT/scripts/generate_figure2b_primary_endpoint_bootstrap.py"

echo "Rebuilding approved Figure 2(b) national state-bootstrap whiskers (diagnostic)..."
"$PYTHON" "$ROOT/scripts/generate_figure2b_state_bootstrap.py"

echo "Rebuilding Figure 2(c) cap variants..."
"$PYTHON" "$ROOT/scripts/generate_figure2c.py"

echo "Rebuilding strict capped Figure 2(d) transition panel for audit..."
"$PYTHON" "$ROOT/scripts/generate_figure2d_clean.py"

echo "Rebuilding approved Figure 2(d) transition panel under fixed district area and historically observed cereals..."
"$PYTHON" "$ROOT/scripts/generate_figure2d_no_historical_cap_core.py"

echo "Rebuilding closest-to-published Figure 2(d) transition panel..."
"$PYTHON" "$ROOT/scripts/generate_figure2d_closest_to_published.py"

echo "Writing Figure 2 cap-variant audit..."
"$PYTHON" "$ROOT/scripts/audit_figure2_cap_variants.py"

echo "Writing Figure 2 legacy-faithful audit..."
"$PYTHON" "$ROOT/scripts/audit_figure2_legacy_faithful.py"

echo "Assembling Supplementary MSP benchmark Figure 2 composite..."
"$PYTHON" "$ROOT/scripts/assemble_si_msp_benchmark_figure2.py"

echo "Done. See:"
echo "  $ROOT/figures"
echo "  $ROOT/data/generated/figure2_cap_variant_audit.md"
echo "  $ROOT/data/generated/figure2_legacy_faithful_audit.md"
