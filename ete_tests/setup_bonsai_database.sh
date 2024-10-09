#!/usr/bin/env bash
set -e

# bootstrap bonsai database
bonsai_api setup --help

# run commands given to container
echo "Executing command: ${@}"
exec "${@}"