# Bonsai

Analyze outbreak, antimicrobial resistance and virulence factors in bacteria.

Intended to visualize results from [JASEN](https://github.com/genomic-medicine-sweden/JASEN) pipeline.

## Installation

See the [documentation](https://bonsai-wgs.readthedocs.io/en/latest/) for instructions on how to install and configure Bonsai.

### Building MinHash on constrained legacy hosts

Use `docker-compose.legacy.env` to select the low-thread Conda build path. Build
the two services separately because older Compose v1 releases do not permit a
parallel-operation limit below two:

```bash
docker-compose --env-file docker-compose.legacy.env \
  -f docker-compose.yml -f docker-compose.override.yml \
  build --pull --no-cache minhash_service

docker-compose --env-file docker-compose.legacy.env \
  -f docker-compose.yml -f docker-compose.override.yml \
  build --pull --no-cache minhash_cron_service
```

If `--env-file` is unsupported, source the file before running those build
commands:

```bash
set -a
. ./docker-compose.legacy.env
set +a
```
