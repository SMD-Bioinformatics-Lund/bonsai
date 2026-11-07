#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
BONSAI_PROJECT_DATA="${BONSAI_PROJECT_DATA:-${HOME}/data/codex/bonsai}"
export BONSAI_TEST_RUN_DIR="${BONSAI_TEST_RUN_DIR:-$(readlink -f "${BONSAI_PROJECT_DATA}/runs/species-ui-active")}"
export DOCKER_CONFIG="${DOCKER_CONFIG:-${BONSAI_PROJECT_DATA}/tools/docker-config}"
compose=(docker compose -f "${REPO_ROOT}/docker-compose.yml"
  -f "${REPO_ROOT}/docker-compose.dev.yml" -f "${REPO_ROOT}/docker-compose.local-test.yml"
  -f "${REPO_ROOT}/docker-compose.species-test.yml" -f "${REPO_ROOT}/docker-compose.general-fixes.yml")

case "${1:-status}" in
  build-js)
    # This image contains the same Node toolchain used for the baseline build.
    mkdir -p "${BONSAI_TEST_RUN_DIR}/frontend-build" "${REPO_ROOT}/frontend/bonsai_app/static/build"
    docker run --rm --user "$(id -u):$(id -g)" \
      -v "${REPO_ROOT}/frontend/web:/app/frontend/web:ro" \
      -v "${BONSAI_TEST_RUN_DIR}/frontend-build:/app/frontend/build" \
      -w /app/frontend bonsai-general-node-tools npm run build
    ;;
  up) "${compose[@]}" up -d --no-deps api frontend ;;
  status) "${compose[@]}" ps ;;
  *) echo "Usage: $0 {build-js|up|status}" >&2; exit 2 ;;
esac
