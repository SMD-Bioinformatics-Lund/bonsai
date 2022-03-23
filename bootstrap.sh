#!/bin/bash
set -e
docker-compose run --rm api python run_mimer.py index
docker-compose up -d
./add_samples.sh
