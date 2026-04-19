#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-/workspace}"

if [[ ! -d "$REPO_ROOT" ]]; then
  echo "Expected repository root at $REPO_ROOT inside the mounted workspace." >&2
  exit 1
fi

exec "$REPO_ROOT/code_final/run_final_revision2_batch.sh" "$@"
