#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(CDPATH= cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
workers=(bonsai-species-test-minhash_service-1 bonsai-species-test-minhash_cron_service-1
         bonsai-species-test-ska_service-1 bonsai-species-test-allele_cluster_service-1)
case "${1:-scope}" in
  scope)
    python3 - "${REPO_ROOT}/docs/local-testing/bounded-scope.json" <<'PY'
import json,sys
scope=json.load(open(sys.argv[1]))
print(scope['purpose'])
for increment in scope['increments']:
    print('\nIncrement: '+increment['id'])
    for action in increment['actions']:print('  '+action)
print('\nExcluded:')
for action in scope['excluded']:print('  '+action)
print('\n'+scope['on_platform_stop'])
print('\n'+scope['limitations'])
PY
    ;;
  workers-stop) docker stop "${workers[@]}" ;;
  workers-start) docker start "${workers[@]}" ;;
  status) docker inspect --format '{{.Name}} {{.State.Status}}' "${workers[@]}" ;;
  guards) python3 -m unittest discover -s "${REPO_ROOT}/scripts/tests" -p test_bounded_scope.py ;;
  *) echo "Usage: $0 {scope|workers-stop|workers-start|status|guards}" >&2; exit 2 ;;
esac
