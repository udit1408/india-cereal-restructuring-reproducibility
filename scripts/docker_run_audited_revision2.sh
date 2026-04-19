#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORKSPACE_ROOT="$(cd "$ROOT/.." && pwd)"
IMAGE_TAG="${IMAGE_TAG:-shekhar-nature-r2-audited:latest}"

docker build -f "$ROOT/container/Dockerfile" "$ROOT" -t "$IMAGE_TAG"
docker run --rm \
  -e WORKSPACE_ROOT="$WORKSPACE_ROOT" \
  -v "$WORKSPACE_ROOT:$WORKSPACE_ROOT" \
  -w "$WORKSPACE_ROOT" \
  "$IMAGE_TAG" \
  "$@"
