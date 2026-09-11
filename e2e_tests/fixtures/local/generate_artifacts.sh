#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(CDPATH= cd -- "${SCRIPT_DIR}/../../.." && pwd)"
FIXTURE_ROOT="${REPO_ROOT}/e2e_tests/fixtures/local"
COMPOSE_FILES=(-f "${REPO_ROOT}/docker-compose.yml" -f "${REPO_ROOT}/docker-compose.dev.yml")

python3 "${SCRIPT_DIR}/generate/generate_fixtures.py"

docker compose "${COMPOSE_FILES[@]}" build minhash_service ska_service

while IFS= read -r fasta; do
    sample_dir="$(dirname -- "${fasta}")"
    sample_id="$(basename -- "${fasta}" .fasta)"
    relative_dir="${sample_dir#${FIXTURE_ROOT}/}"
    signature="${sample_dir}/${sample_id}.sig"
    ska_index="${sample_dir}/${sample_id}_ska_index.skf"

    if [[ ! -f "${signature}" ]]; then
        docker compose "${COMPOSE_FILES[@]}" run --rm --no-deps \
            --user "$(id -u):$(id -g)" \
            -v "${FIXTURE_ROOT}:/fixtures" \
            minhash_service \
            sourmash sketch dna \
                -p k=31,scaled=1000,noabund \
                --name "${sample_id}" \
                -o "/fixtures/${relative_dir}/${sample_id}.sig" \
                "/fixtures/${relative_dir}/${sample_id}.fasta" \
                < /dev/null
    fi

    if [[ ! -f "${ska_index}" ]]; then
        docker compose "${COMPOSE_FILES[@]}" run --rm --no-deps \
            --user "$(id -u):$(id -g)" \
            -v "${FIXTURE_ROOT}:/fixtures" \
            ska_service \
            ska build \
                -k 31 \
                -o "/fixtures/${relative_dir}/${sample_id}_ska_index" \
                "/fixtures/${relative_dir}/${sample_id}.fasta" \
                < /dev/null
    fi
done < <(find "${FIXTURE_ROOT}/samples" -type f -name 'synthetic_*.fasta' | sort)

(
    cd "${FIXTURE_ROOT}"
    find samples -type f ! -name checksums.sha256 -print0 \
        | sort -z \
        | xargs -0 sha256sum > checksums.sha256
)

echo "Generated synthetic genomes, sourmash signatures, SKA indexes, and checksums."
