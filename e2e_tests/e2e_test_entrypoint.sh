#!/usr/bin/env bash
set -e

bash /home/worker/load_test_samples.sh

echo "Executing command: ${@}"
exec "${@}"