# Synthetic local-test data

This directory contains deterministic test data generated entirely from
pseudo-random DNA. It contains no patient, clinical, or production data and is
not intended to be biologically meaningful.

By default, the dataset has five synthetic `mtuberculosis` samples and five
synthetic `saureus` samples. It exercises:

- sourmash MinHash signatures (`k=31`, `scaled=1000`, no abundance tracking)
- SKA2 split-kmer indexes (`k=31`)
- Bracken species-result parsing
- QUAST QC-result parsing
- MLST and chewBBACA/cgMLST parsing for the `saureus` group

The samples use nested, deterministic substitutions. This gives the clustering
services a stable range of distances while keeping the data easy to regenerate.

## Generate or regenerate artifacts

Set `SAMPLE_COUNT` near the top of
`generate/generate_fixtures.py` to change the number of samples generated for
each species. Mutation distances are distributed automatically across the
configured sample count.

From the repository root:

```bash
bash e2e_tests/fixtures/local/generate_artifacts.sh
```

The script builds and uses the repository's MinHash and SKA development images,
so artifacts are created with the same versions used by the application.
Generated `.sig` and `.skf` files are rebuilt on every run, and sample
directories above the configured count are removed. This prevents stale
artifacts when `SAMPLE_COUNT` changes.

## Start a clean local-test instance

The overlay creates a separate Compose project, stores MongoDB and MinHash data
in test-only named volumes, and gives the SKA worker read-only access to the
generated indexes. Its containers, network, data, and host ports are isolated
from the normal development stack.

```bash
docker compose \
  -f docker-compose.yml \
  -f docker-compose.dev.yml \
  -f docker-compose.local-test.yml \
  --profile init up -d --build
```

Watch bootstrap, upload, and indexing:

```bash
docker compose \
  -f docker-compose.yml \
  -f docker-compose.dev.yml \
  -f docker-compose.local-test.yml \
  logs -f bootstrap test-data-seeder minhash_service ska_service
```

The API's `bonsai-api check-paths` command is currently incompatible with the
UUID-based sample schema. Until that command is fixed, inspect the upload and
worker logs:

```bash
docker compose \
  -f docker-compose.yml \
  -f docker-compose.dev.yml \
  -f docker-compose.local-test.yml \
  logs test-data-seeder minhash_service ska_service
```

Run the API smoke test after `test-data-seeder` has exited successfully. It
verifies sample counts, parsed results, and live MinHash, SKA, MLST, and cgMLST
clustering:

```bash
python3 e2e_tests/fixtures/local/smoke_test.py
```

The UI is available at <http://localhost:18000> and the API at
<http://localhost:18001>. The alternate ports allow this stack to run alongside
the normal development stack. Local credentials are:

| Role | Username | Password |
| --- | --- | --- |
| Administrator | `admin` | `admin123` |
| User | `user_one` | `user123` |
| Uploader | `uploader` | `user123` |

## Reset

Stop the local-test stack and remove only its named volumes:

```bash
docker compose \
  -f docker-compose.yml \
  -f docker-compose.dev.yml \
  -f docker-compose.local-test.yml \
  --profile init down -v --remove-orphans
```

Enabling the profile also removes its completed `bootstrap` and
`test-data-seeder` containers, ensuring they run again on the next start.
`--remove-orphans` cleans up one-shot services removed from the Compose files.
This removes the local-test MongoDB and MinHash volumes. The normal development
containers, network, and data are not part of the `bonsai-local-test` project.
