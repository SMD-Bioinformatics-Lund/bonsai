#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
BONSAI_PROJECT_DATA="${BONSAI_PROJECT_DATA:-${HOME}/data/codex/bonsai}"
export BONSAI_TEST_RUN_DIR="${BONSAI_TEST_RUN_DIR:-$(readlink -f "${BONSAI_PROJECT_DATA}/runs/species-ui-active")}"
export DOCKER_CONFIG="${DOCKER_CONFIG:-${BONSAI_PROJECT_DATA}/tools/docker-config}"
compose=(docker compose -f "${REPO_ROOT}/docker-compose.yml"
  -f "${REPO_ROOT}/docker-compose.dev.yml" -f "${REPO_ROOT}/docker-compose.local-test.yml"
  -f "${REPO_ROOT}/docker-compose.species-test.yml" -f "${REPO_ROOT}/docker-compose.general-fixes.yml"
  -f "${REPO_ROOT}/docker-compose.parser-sdk.yml")
case "${1:-status}" in
  up)
    test -f "${REPO_ROOT}/bonsai-sdk/src/bonsai_libs/parse/__init__.py"
    "${compose[@]}" up -d --no-deps api frontend
    ;;
  status) "${compose[@]}" ps ;;
  restore-image-sdk) bash "${REPO_ROOT}/scripts/general-test.sh" up ;;
  *) echo "Usage: $0 {up|status|restore-image-sdk}" >&2; exit 2 ;;
esac
