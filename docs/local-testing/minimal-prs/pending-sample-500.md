# Render pending records without pipeline metadata

A valid record without a completed pipeline is accepted, but the summary assumes pipeline metadata exists and returns HTTP 500. Handle absent pipeline/database metadata and show the pending state.

### How to setup and perform the tests

1. Keep the reusable audit harness available on `fix/critical-ui-release-pass` in `/home/jakob/src/codex/bonsai`. The production branch intentionally contains only the reported fix. Docker images and generic test dependencies are already cached on this machine.
2. From that checkout, run:

```bash
python3 scripts/verify_minimal_prs.py --only PENDING-SAMPLE-500
```

The harness extracts the candidate Git tree, so switching the running application checkout is unnecessary. Candidate checked: `f24e6a59cbd5aa2e9b98cd427f278ac05277910b`.

### Expected outcome

Empty and metadata-only records must open with clear pending feedback.

Recorded result: 1 focused checks passed (frontend). Logs and source heads are pinned in the local verification ledger. Only optional display metadata is handled.

### Additional context

- Finding: `PENDING-SAMPLE-500`; apparent priority: P1.
- Repository: Bonsai; base: `development` (`21eccf7075fb59a897cb2ae86b0d6cdb95d0089c`).
- +6/-2 production lines in 2 file(s), relative to development.
- Git prerequisites: None.
- Paired repository candidate: None.
- Normal trigger: A record is opened before a pipeline is attached, or remains metadata-only. The ingestion delay determines how often this state is seen.
- Selection assessment: Early review.
- Scope limit: Targeted fix; stated validation limits apply.

Publication is performed by the user when selected:

```bash
git -C /home/jakob/src/codex/bonsai push -u origin pr/pending-sample-500
```
