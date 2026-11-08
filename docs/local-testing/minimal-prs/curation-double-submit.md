# Submit a confirmation once and render refreshed state

The original browser run saved a decision, returned HTTP 409 and displayed stale state. The baseline controller calls the creation service twice for one confirmation. Remove the duplicate service call and reload state after the save.

### How to setup and perform the tests

1. Keep the reusable audit harness available on `fix/critical-ui-release-pass` in `/home/jakob/src/codex/bonsai`. The production branch intentionally contains only the reported fix. Docker images and generic test dependencies are already cached on this machine.
2. From that checkout, run:

```bash
python3 scripts/verify_minimal_prs.py --only CURATION-DOUBLE-SUBMIT
```

The harness extracts the candidate Git tree, so switching the running application checkout is unnecessary. Candidate checked: `aa554c2ad2cbb0adf9eccf8487b237bdc9a583e0`.

### Expected outcome

Call the service once and render refreshed saved state; verify with stubs before any separately scoped write test.

Recorded result: 2 focused checks passed (frontend). Logs and source heads are pinned in the local verification ledger. Only generic stubbed service calls and refreshed rendering were tested; no live decision was written.

### Additional context

- Finding: `CURATION-DOUBLE-SUBMIT`; apparent priority: P1.
- Repository: Bonsai; base: `development` (`21eccf7075fb59a897cb2ae86b0d6cdb95d0089c`).
- +1/-5 production lines in 2 file(s), relative to development.
- Git prerequisites: None.
- Paired repository candidate: None.
- Normal trigger: One Confirm action invokes the same save twice. The first save can persist before the second call reports a conflict.
- Selection assessment: Early review.
- Scope limit: Targeted fix; stated validation limits apply.

Publication is performed by the user when selected:

```bash
git -C /home/jakob/src/codex/bonsai push -u origin pr/curation-double-submit
```
