# Synthetic local-test data

This directory contains deterministic test data generated entirely from
pseudo-random DNA. It contains no patient, clinical, or production data and is
not intended to be biologically meaningful.

The dataset has five synthetic `mtuberculosis` samples and five synthetic
`saureus` samples. It exercises:

- sourmash MinHash signatures (`k=31`, `scaled=1000`, no abundance tracking)
- SKA2 split-kmer indexes (`k=31`)
- Bracken species-result parsing
- QUAST QC-result parsing
- MLST and chewBBACA/cgMLST parsing for the `saureus` group

The samples use nested, deterministic substitutions. This gives the clustering
services a stable range of distances while keeping the data easy to regenerate.

## Generate or regenerate artifacts

From the repository root:

```bash
bash e2e_tests/fixtures/local/generate_artifacts.sh
```

The script builds and uses the repository's MinHash and SKA development images,
so artifacts are created with the same versions used by the application. It
does not overwrite existing `.sig` or `.skf` files. Remove an individual
derived artifact before regenerating that artifact.

## Start a clean local-test instance

The overlay uses named volumes instead of the normal development MongoDB bind
mount and gives the SKA worker read-only access to the generated indexes.

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
  logs test-data-seeder test-data-groups minhash_service ska_service
```

Run the API smoke test after `test-data-seeder` and `test-data-groups` have
exited successfully. It verifies sample counts, group membership, parsed
results, and live MinHash, SKA, MLST, and cgMLST clustering:

```bash
python3 e2e_tests/fixtures/local/smoke_test.py
```

The UI is available at <http://localhost:18000> and the API at
<http://localhost:18001>. The alternate ports and Compose project name allow
the local-test stack to run alongside the normal development stack. Local
credentials are:

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
  down -v
```

The named volumes, network, container names, and host ports are isolated from
the normal development stack.
