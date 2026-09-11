#!/usr/bin/env bash
set -euo pipefail

# Used together with synthetic dataset to generate sourmash and SKA outputs

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(CDPATH= cd -- "${SCRIPT_DIR}/../../.." && pwd)"
FIXTURE_ROOT="${REPO_ROOT}/e2e_tests/fixtures/local"
COMPOSE_FILES=(-f "${REPO_ROOT}/docker-compose.yml" -f "${REPO_ROOT}/docker-compose.dev.yml")

python3 "${SCRIPT_DIR}/generate/generate_fixtures.py"

docker compose "${COMPOSE_FILES[@]}" build minhash_service ska_service

# Mutation distances may change when SAMPLE_COUNT changes, so rebuild derived
# artifacts instead of retaining indexes generated from older FASTA content.
find "${FIXTURE_ROOT}/samples" -type f \
    \( -name '*.sig' -o -name '*_ska_index.skf' \) -delete

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

echo "Generated synthetic genomes, sourmash signatures, and SKA indexes."
