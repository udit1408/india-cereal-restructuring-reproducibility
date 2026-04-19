#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="$ROOT/_audit/Nitrogen-Surplus-restructuring/.venv/bin/python"

echo "Rebuilding approved Figure 2(a) assets under fixed district area and historically observed cereals..."
"$PYTHON" "$ROOT/scripts/export_figure2a_assets.py"

echo "Rebuilding approved Figure 2(b) endpoint panel under fixed district area and historically observed cereals..."
"$PYTHON" "$ROOT/scripts/generate_figure2b_clean.py" --no-historical-caps --output-stem figure2b_no_historical_cap_core

echo "Rebuilding approved Figure 2(b) national state-bootstrap whiskers..."
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

echo "Assembling refreshed Figure 2 composite..."
"$PYTHON" "$ROOT/scripts/assemble_figure2_composite.py"

echo "Done. See:"
echo "  $ROOT/figures"
echo "  $ROOT/data/generated/figure2_cap_variant_audit.md"
echo "  $ROOT/data/generated/figure2_legacy_faithful_audit.md"
