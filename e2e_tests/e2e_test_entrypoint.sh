#!/usr/bin/env bash
set -e

bash /app/load_test_samples.sh

echo "Executing command: ${@}"
exec "${@}"