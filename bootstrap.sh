#!/bin/bash
set -e
docker-compose run --rm api python run_mimer.py index
docker-compose run --rm api python run_mimer.py create-user -u creator -p creator -r admin
docker-compose up -d