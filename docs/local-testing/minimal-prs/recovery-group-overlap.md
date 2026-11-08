# Send only changed fields from the group editor

Saving a description in a stale second tab reverts the name saved in the first tab. Unchanged fields are resent in the full payload. Send only changed core fields and changed column selection.

### How to setup and perform the tests

1. Keep the reusable audit harness available on `fix/critical-ui-release-pass` in `/home/jakob/src/codex/bonsai`. The production branch intentionally contains only the reported fix. Docker images and generic test dependencies are already cached on this machine.
2. From that checkout, run:

```bash
python3 scripts/verify_minimal_prs.py --only RECOVERY-GROUP-OVERLAP
```

The harness extracts the candidate Git tree, so switching the running application checkout is unnecessary. Candidate checked: `e049aec434621b10c094ff6888dda27abf8dec3f`.

### Expected outcome

Save different fields from two tabs and retain both values.

Recorded result: 1 focused checks passed (node). Logs and source heads are pinned in the local verification ledger. Same-field last-writer behavior and pending-save controls remain separate P2 issues.

### Additional context

- Finding: `RECOVERY-GROUP-OVERLAP`; apparent priority: P1.
- Repository: Bonsai; base: `development` (`21eccf7075fb59a897cb2ae86b0d6cdb95d0089c`).
- +17/-7 production lines in 3 file(s), relative to development.
- Git prerequisites: None.
- Paired repository candidate: None.
- Normal trigger: One user leaves a group editor open while another changes a different field. Saving the older form overwrites the unrelated change.
- Selection assessment: Concurrency-dependent.
- Scope limit: Targeted fix; stated validation limits apply.

Publication is performed by the user when selected:

```bash
git -C /home/jakob/src/codex/bonsai push -u origin pr/recovery-group-overlap
```
