#!/usr/bin/env bash
set -Eeuo pipefail

API_URL="${API_URL:-http://api:8000/}"
ADMIN_USER="${ADMIN_USER:-admin}"
ADMIN_PASS="${ADMIN_PASS:-admin}"

for file in /app/fixtures/samples/*.yaml; do
  echo "Uploading sample $file"
  /app/upload_sample.py \
    --user     "$ADMIN_USER" \
    --password "$ADMIN_PASS" \
    --api      "$API_URL" \
    --input    "$file"
done

echo "Upload completed."