#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
APPROVED_BASENAME="fig2_main_revision2"
SOURCE_PDF="$ROOT/figures/${APPROVED_BASENAME}.pdf"
ARTICLE_DIR="$ROOT/R_2_sources/article"
PDF_DIR="$ROOT/R_2_PDFs"

if [[ ! -f "$SOURCE_PDF" ]]; then
  echo "Missing approved Figure 2: $SOURCE_PDF" >&2
  exit 1
fi

mkdir -p "$PDF_DIR"
cp "$SOURCE_PDF" "$ARTICLE_DIR/${APPROVED_BASENAME}.pdf"
cp "$SOURCE_PDF" "$PDF_DIR/${APPROVED_BASENAME}.pdf"

echo "Approved Figure 2 synced to:"
echo "  $ARTICLE_DIR/${APPROVED_BASENAME}.pdf"
echo "  $PDF_DIR/${APPROVED_BASENAME}.pdf"
