#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
IMAGE_TAG="${IMAGE_TAG:-shekhar-nature-r2-final:latest}"

docker build -f "$ROOT/container/Dockerfile" "$ROOT" -t "$IMAGE_TAG"
docker run --rm \
  -e REPO_ROOT=/workspace \
  -v "$ROOT:/workspace" \
  -w /workspace \
  "$IMAGE_TAG" \
  "$@"
