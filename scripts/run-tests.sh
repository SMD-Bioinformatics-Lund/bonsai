#!/usr/bin/env bash
set -euo pipefail

# Run tests per service
pytest frontend/tests
pytest api/tests
pytest audit_log_service/tests
pytest minhash_service/tests
pytest notification_service/tests
pytest allele_cluster_service/tests