#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
BONSAI_PROJECT_DATA="${BONSAI_PROJECT_DATA:-${HOME}/data/codex/bonsai}"
if [[ -z "${BONSAI_TEST_RUN_DIR:-}" ]]; then
    active_run="${BONSAI_PROJECT_DATA}/runs/species-ui-active"
    if [[ "${1:-status}" != "prepare" && -d "${active_run}" ]]; then
        BONSAI_TEST_RUN_DIR="$(readlink -f "${active_run}")"
    else
        BONSAI_TEST_RUN_DIR="${BONSAI_PROJECT_DATA}/runs/$(date -u +%Y-%m-%d)-species-ui"
    fi
fi
export BONSAI_TEST_RUN_DIR
export DOCKER_CONFIG="${DOCKER_CONFIG:-${BONSAI_PROJECT_DATA}/tools/docker-config}"
compose=(docker compose --parallel 1 -f "${REPO_ROOT}/docker-compose.yml"
    -f "${REPO_ROOT}/docker-compose.dev.yml" -f "${REPO_ROOT}/docker-compose.local-test.yml"
    -f "${REPO_ROOT}/docker-compose.species-test.yml")

action="${1:-status}"
if [[ "${action}" != "status" && "${action}" != "logs" ]]; then
    mkdir -p "${BONSAI_TEST_RUN_DIR}/logs"
    exec > >(tee "${BONSAI_TEST_RUN_DIR}/logs/${action}-$(date -u +%Y%m%dT%H%M%SZ).log") 2>&1
fi

case "${1:-status}" in
    prepare)
        python3 "${REPO_ROOT}/e2e_tests/fixtures/local/generate/generate_species_fixtures.py" \
            --root "${BONSAI_TEST_RUN_DIR}/fixtures"
        mkdir -p "${BONSAI_PROJECT_DATA}/runs"
        ln -sfnT "${BONSAI_TEST_RUN_DIR}" "${BONSAI_PROJECT_DATA}/runs/species-ui-active"
        ;;
    build)
        shift
        "${compose[@]}" --progress plain build "$@"
        ;;
    indexes)
        "${compose[@]}" run -T --rm --no-deps --user "$(id -u):$(id -g)" \
            -v "${BONSAI_TEST_RUN_DIR}/fixtures:/fixtures" minhash_service /bin/bash -c '
                set -euo pipefail
                while IFS= read -r fasta; do
                    sourmash sketch dna -p k=31,scaled=1000,noabund --name "$(basename "${fasta}" .fasta)" \
                        -o "${fasta%.fasta}.sig" "${fasta}"
                done < <(find /fixtures/samples /fixtures/cases/genomes -name "synthetic_*.fasta" | sort)
            '
        "${compose[@]}" run -T --rm --no-deps --user "$(id -u):$(id -g)" \
            -v "${BONSAI_TEST_RUN_DIR}/fixtures:/fixtures" ska_service /bin/bash -c '
                set -euo pipefail
                while IFS= read -r fasta; do
                    ska build -k 31 -o "${fasta%.fasta}_ska_index" "${fasta}"
                done < <(find /fixtures/samples /fixtures/cases/genomes -name "synthetic_*.fasta" | sort)
            '
        ;;
    infra)
        "${compose[@]}" up -d mongodb redis mongo-init mailhog
        ;;
    resources)
        docker build -t bonsai-species-fixture-tools "${REPO_ROOT}/e2e_tests/fixtures/local/generate"
        docker run --rm --user "$(id -u):$(id -g)" \
            -v "${BONSAI_TEST_RUN_DIR}/fixtures:/fixtures" bonsai-species-fixture-tools
        ;;
    validate)
        "${compose[@]}" run -T --rm --no-deps \
            -v "${BONSAI_TEST_RUN_DIR}/fixtures:/fixtures:ro" api \
            python /fixtures/validate_species_fixtures.py --root /fixtures
        "${compose[@]}" run -T --rm --no-deps \
            -v "${BONSAI_TEST_RUN_DIR}/fixtures:/fixtures:ro" minhash_service \
            python /fixtures/validate_indexes.py
        ;;
    up)
        "${compose[@]}" up -d
        ;;
    seed)
        "${compose[@]}" --profile init up -d
        ;;
    logs)
        shift
        "${compose[@]}" --profile init logs --tail 100 "$@"
        ;;
    stop)
        "${compose[@]}" --profile init stop
        ;;
    status)
        "${compose[@]}" --profile init ps -a
        ;;
    *)
        echo "Usage: $0 {prepare|build [services...]|indexes|resources|validate|infra|up|seed|logs [services...]|stop|status}" >&2
        exit 2
        ;;
esac
