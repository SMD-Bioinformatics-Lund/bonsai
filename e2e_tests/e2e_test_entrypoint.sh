#!/usr/bin/env bash
set -e

# Load test samples
# =================
for file in /app/fixtures/samples/*.yaml; do
  echo "Uploading sample $file"
  /app/upload_sample.py \
    --user     admin \
    --password admin \
    --api      http://api:8000/ \
    --input    "$file"
done

# Run container CMD
# =================
echo "Executing command: ${@}"
exec "${@}"