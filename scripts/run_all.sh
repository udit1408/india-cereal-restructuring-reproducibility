#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
INPUT_DIR="$ROOT/data/input"
OUTPUT_DIR="$ROOT/data/generated"
TEX_DIR="$ROOT/tex"
BUILD_DIR="$ROOT/build"
PDF_DIR="$ROOT/R_2_PDFs"
NOTE_BASENAME="revenue_robustness_note"
DELIVERABLE_BASENAME="release_revenue_robustness_note"
AUDIT_PY="$ROOT/_audit/Nitrogen-Surplus-restructuring/.venv/bin/python"

python3 "$ROOT/scripts/build_sensitivity_outputs.py" "$INPUT_DIR" "$OUTPUT_DIR"
"$AUDIT_PY" "$ROOT/scripts/generate_si_revenue_robustness_figure.py"
"$AUDIT_PY" "$ROOT/scripts/generate_si_revenue_benchmark_endpoint_sensitivity.py"

mkdir -p "$BUILD_DIR"
mkdir -p "$PDF_DIR"
cd "$TEX_DIR"
pdflatex -interaction=nonstopmode -output-directory "$BUILD_DIR" "$NOTE_BASENAME.tex" >/dev/null
pdflatex -interaction=nonstopmode -output-directory "$BUILD_DIR" "$NOTE_BASENAME.tex" >/dev/null
cp "$BUILD_DIR/$NOTE_BASENAME.pdf" "$PDF_DIR/$DELIVERABLE_BASENAME.pdf"

echo "Built PDF: $BUILD_DIR/$NOTE_BASENAME.pdf"
echo "Copied deliverable: $PDF_DIR/$DELIVERABLE_BASENAME.pdf"
