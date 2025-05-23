#!/usr/bin/env bash
set -e

# Load test samples
# =================
find /app/fixtures/samples/ -name *yaml -exec prp bonsai-upload --username admin --password admin --api http://api:8000/ {} \;

# Run container CMD
# =================
echo "Executing command: ${@}"
exec "${@}"