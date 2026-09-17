#!/bin/sh
set -eu

manifest_list="$(mktemp)"
find /data/samples -type f -name '*.manifest.yml' | sort > "${manifest_list}"

while IFS= read -r manifest; do
    echo "Uploading synthetic fixture: ${manifest}"
    prp bonsai upload \
        --api "${BONSAI_API}" \
        --username "${BONSAI_USER}" \
        --password "${BONSAI_PASSWD}" \
        "${manifest}"
done < "${manifest_list}"

python3 /data/scenario_test.py --setup-only \
    --api "${BONSAI_API}" --username "${BONSAI_USER}" --password "${BONSAI_PASSWD}"

echo "All synthetic local-test fixtures uploaded."
