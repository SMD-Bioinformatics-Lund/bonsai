# Project requested EMM fields from their current stored paths

Two requested summary-column paths do not match the existing projection alias. Positive stored values are omitted even when those columns are requested. Correct the two projection paths to the current stored fields.

### How to setup and perform the tests

1. Keep the reusable audit harness available on `fix/critical-ui-release-pass` in `/home/jakob/src/codex/bonsai`. The production branch intentionally contains only the reported fix. Docker images and generic test dependencies are already cached on this machine.
2. From that checkout, run:

```bash
python3 scripts/verify_minimal_prs.py --only DISPLAY-EMM-TABLE
```

The harness extracts the candidate Git tree, so switching the running application checkout is unnecessary. Candidate checked: `ca7a7c22cc5f95a3868e4e314d2313a9b9068c94`.

### Expected outcome

Return the supplied type and cluster through both requested projection paths. Default layouts are a separate configuration choice.

Recorded result: 1 focused checks passed (mongo). Logs and source heads are pinned in the local verification ledger. A two-expression fix; enabling columns by default is a separate layout decision.

### Additional context

- Finding: `DISPLAY-EMM-TABLE`; apparent priority: P1.
- Repository: Bonsai; base: `development` (`21eccf7075fb59a897cb2ae86b0d6cdb95d0089c`).
- +2/-2 production lines in 1 file(s), relative to development.
- Git prerequisites: None.
- Paired repository candidate: None.
- Normal trigger: A client or group layout explicitly requests EMM type/cluster columns. The observed default layout does not request them.
- Selection assessment: Early review.
- Scope limit: Targeted fix; stated validation limits apply.

Publication is performed by the user when selected:

```bash
git -C /home/jakob/src/codex/bonsai push -u origin pr/display-emm-table
```
