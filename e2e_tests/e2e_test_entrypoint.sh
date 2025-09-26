#!/usr/bin/env bash
set -e

# Run container CMD
# =================
echo "Executing command: ${@}"
exec "${@}"