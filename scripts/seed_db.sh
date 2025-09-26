#!/usr/bin/env bash
set -Eeuo pipefail

# Use a small persistent marker to avoid reseeding
SEED_MARKER_FILE="/var/lib/app-seed/.seeded"

if [ -f "$SEED_MARKER_FILE" ]; then
  echo "Seed already performed—skipping."
  exit 0
fi

echo "Bootstrapping bonsai database…"

# 1. create index and admin user
bonsai_api setup

# 2. create normal user
bonsai_api create-user -u user -p user -m user@mail.com -r user

# 3. create sample groups
bonsai_api create-group -i mtuberculosis -n "M. tuberculosis" -d "Tuberculosis test samples"
bonsai_api create-group -i saureus       -n "S. aureus"       -d "MRSA test samples"
bonsai_api create-group -i ecoli         -n "E. coli"         -d "E. coli test samples"
bonsai_api create-group -i streptococcus -n "Streptococcus spp" -d "S. pyogenes test samples"

# mark as done
mkdir -p "$(dirname "$SEED_MARKER_FILE")"
touch "$SEED_MARKER_FILE"

echo "Seeding complete."