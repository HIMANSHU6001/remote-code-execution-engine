#!/usr/bin/env bash
# Build all RCE sandbox Docker images.
# Run from the repository root: bash scripts/build_images.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

build() {
  local name="$1"
  local context="$2"
  echo "==> Building rce-${name}:latest"
  docker build -t "rce-${name}:latest" "${REPO_ROOT}/docker/${context}"
}

build cpp    cpp
build clang  clang
build java   java
build python python
build js     js

echo ""
echo "All images built successfully."
docker images | grep "^rce-"
