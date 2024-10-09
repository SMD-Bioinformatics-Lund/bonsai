#!/usr/bin/env bash
set -e

# bootstrap bonsai database
bonsai_api setup
bonsai_api create-user -u user -p user -m user@mail.com -r user

# run commands given to container
echo "Executing command: ${@}"
exec "${@}"