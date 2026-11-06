#!/bin/sh
set -eu

manifest_list="$(mktemp)"
trap 'rm -f "${manifest_list}"' EXIT
find /data/samples -type f -name '*.manifest.yml' | sort > "${manifest_list}"
while IFS= read -r manifest; do
    echo "Uploading synthetic fixture: ${manifest}"
    python -c 'from prp.cli import cli; cli()' bonsai upload \
        --api "${BONSAI_API}" --username "${BONSAI_USER}" --password "${BONSAI_PASSWD}" \
        "${manifest}"
done < "${manifest_list}"
python /data/scenario_test.py --setup-only \
    --api "${BONSAI_API}" --username "${BONSAI_USER}" --password "${BONSAI_PASSWD}"
