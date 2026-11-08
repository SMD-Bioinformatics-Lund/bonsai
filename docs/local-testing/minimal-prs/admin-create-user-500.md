# Handle typed SDK not-found during local user creation

A normal unknown username produces the SDK's NotFoundError, while form validation catches the older HTTPError type. Creation returns HTTP 500. Catch the SDK's typed not-found exception during the existence check.

### How to setup and perform the tests

1. Keep the reusable audit harness available on `fix/critical-ui-release-pass` in `/home/jakob/src/codex/bonsai`. The production branch intentionally contains only the reported fix. Docker images and generic test dependencies are already cached on this machine.
2. From that checkout, run:

```bash
python3 scripts/verify_minimal_prs.py --only ADMIN-CREATE-USER-500
```

The harness extracts the candidate Git tree, so switching the running application checkout is unnecessary. Candidate checked: `e01528db104ccb7d392441f42cfe742ee45f5e8e`.

### Expected outcome

Create and list one valid account; invalid fields must produce form feedback without a write.

Recorded result: 1 focused checks passed (frontend). Logs and source heads are pinned in the local verification ledger. A small deterministic fix for the local-account administration path.

### Additional context

- Finding: `ADMIN-CREATE-USER-500`; apparent priority: P1.
- Repository: Bonsai; base: `development` (`21eccf7075fb59a897cb2ae86b0d6cdb95d0089c`).
- +3/-5 production lines in 1 file(s), relative to development.
- Git prerequisites: None.
- Paired repository candidate: None.
- Normal trigger: An administrator submits a new local account. This is infrequent administration, and may be uncommon if external authentication supplies all users.
- Selection assessment: Early review.
- Scope limit: Targeted fix; stated validation limits apply.

Publication is performed by the user when selected:

```bash
git -C /home/jakob/src/codex/bonsai push -u origin pr/admin-create-user-500
```
