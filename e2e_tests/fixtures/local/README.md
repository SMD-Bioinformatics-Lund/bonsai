# Synthetic local-test data

This directory contains deterministic test data generated entirely from
pseudo-random DNA. It contains no patient, clinical, or production data and is
not intended to be biologically meaningful.

By default, the dataset has ten synthetic `mtuberculosis` samples and ten
synthetic `saureus` samples. It exercises:

- sourmash MinHash signatures (`k=31`, `scaled=1000`, no abundance tracking)
- SKA2 split-kmer indexes (`k=31`)
- Bracken species-result parsing
- QUAST QC-result parsing
- MLST and chewBBACA/cgMLST parsing for the `saureus` group
- TBProfiler and Mykrobe AMR/lineage reports, including distinct predictions
  from both tools and one TBProfiler variant that fails variant QC
- post-alignment QC JSON and samtools stats/coverage/bedcov inputs

The seeder also prepares accepted and rejected variant curations on
`synthetic_tb_001`, including high-level isoniazid resistance, and registers
the optional shared reference and BAM for that sample. These examples support
manual curation, LIMS export and genome-browser testing.

| Scenario | Expected behavior |
| --- | --- |
| TB sample 001 | Three TBProfiler variants; accepted rifampicin and high-level isoniazid calls; rejected ethambutol call. Mykrobe has a different rifampicin variant to detect incorrect source selection. |
| TB sample 002 | TBProfiler has no resistance variants; Mykrobe has no resistant call; lineage remains present. |
| TB sample 003 | Starts uncurated; regression checks create duplicate item/whole-analysis curations, then delete only the curations they created. |
| TB sample 010, when generated | Omits TBProfiler from its manifest; TB LIMS export must return 422 for missing lineage. |
| TB post-alignment QC | 1,000 reads, mean depth 24.5, median depth 20, 80% coverage at 10x and 40% at 30x; restricted mean depth 35. |
| Unseeded cases | Positive/negative virulence and STX, O157/H7 serotype, missing/novel cgMLST alleles, malformed JSON and empty samtools stats. |
| Unseeded genome cases | Identical, unrelated and 4 kb deletion genomes; a small gap alignment for distance semantics. |

Reports are handcrafted parser inputs. Only the signatures, SKA indexes and
optional indexed alignment resources are produced by real tools. The report
metrics are independent of the tiny alignment used for file/browser checks.
These fixtures do not validate upstream biological prediction accuracy.

Only generator code and instructions are tracked. `samples/`, `cases/` and
`resources/` are ignored; no generated reports, genomes, BAMs or indexes need
to be committed. The reference is shared and only 100 kb; its BAM has 20 reads.

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

For full resource and genome-browser coverage, use:

```bash
bash e2e_tests/fixtures/local/generate_artifacts.sh --resources
```

This additionally builds a local tooling image with pinned `pysam==0.23.3`
and generates a FASTA index plus sorted/indexed BAM. The first build downloads
the dependency; subsequent builds can use Docker's cache. No FASTQ dataset or
external reference download is required.

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

Run the expanded API regression scenarios separately:

```bash
python3 e2e_tests/fixtures/local/scenario_test.py --require-current-api
```

They check curated LIMS values and source filtering, duplicate/deleted
curations, QC summary metrics, reference lookup and file serving, duplicate
and blank identifiers, virulence/STX/serotype parsing, missing profiles/indexes,
auxiliary QC uploads, failed-QC classifications and malformed JSON. Temporary scenario samples are
removed in a `finally` block. Run checks after artifact generation finishes;
regeneration temporarily removes indexes.

For an already-seeded stack, prepare the new UI examples without re-uploading
baseline samples:

```bash
python3 e2e_tests/fixtures/local/scenario_test.py --setup-only
```

Setup adds missing reports and example curations, preserves existing decisions,
and reuses the registered reference/resources. It does not replace existing
analysis reports. Use a clean stack if you need to validate changed fixture
contents. The setup command is also run by `seed.sh` on a fresh local-test stack.
It skips optional resources if they have not been built.

Both scripts accept `--api`, `--username` and `--password`. The default API is
the isolated local-test instance. Older APIs explicitly skip checks requiring
PR #504; `--require-current-api` makes the expanded scenario command fail if
the auxiliary-file API is absent.

Reports and sketches can also be checked without running the application:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml \
  -f docker-compose.local-test.yml run --rm --no-deps \
  -v "$PWD/e2e_tests/fixtures/local:/fixtures:ro" \
  --entrypoint python api /fixtures/validate_fixtures.py

docker compose -f docker-compose.yml -f docker-compose.dev.yml \
  -f docker-compose.local-test.yml run --rm --no-deps \
  -v "$PWD/e2e_tests/fixtures/local:/fixtures:ro" \
  --entrypoint python minhash_service /fixtures/validate_indexes.py
```

The first checks reports against the API image's pinned SDK, including the
raw auxiliary-input and missing-auxiliary-input paths. The second checks the
identical/unrelated/deletion sketches and reports checksum sharing in the
baseline. Small mutations can leave scaled sketches identical; this is useful
for detecting sample mapping bugs and should not be interpreted as distinct
MinHash distances for every sample.

Observed application failures on 2026-09-17 remain visible as failed checks:

- Malformed TBProfiler JSON returns HTTP 500 rather than a validation error.
- The current similarity result contract lacks `sample_id` (addressed by the
  pending PR #495).
- MinHash clustering repeats labels and omits samples that share a checksum.

The scripts exit nonzero for regressions; they do not treat these failures as
successful results. MST API selection from pending PR #429 and browser
interaction remain separate checks. The deletion/gap inputs are available for
that PR; the current smoke test exercises the existing hierarchical routes.

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
