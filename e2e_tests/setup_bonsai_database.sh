#!/usr/bin/env bash
set -e

# bootstrap bonsai database
# =========================

# 1. create index and admin user
bonsai_api setup

# 2. create normal user
bonsai_api create-user -u user -p user -m user@mail.com -r user

# 3. create sample groups
bonsai_api create-group -i mtuberculosis -n "M. tuberculosis" -d "Tuberculosis test samples"
bonsai_api create-group -i saureus -n "S. aureus" -d "MRSA test samples"
bonsai_api create-group -i ecoli -n "E. coli" -d "E. coli test samples"

# 4. run commands given to container to start the API
# ===============================
echo "Executing command: ${@}"
exec "${@}"