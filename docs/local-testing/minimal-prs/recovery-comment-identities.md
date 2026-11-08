# Allocate distinct comment IDs under concurrent append

Five simultaneous baseline comments retain all five texts but receive one distinct ID. IDs are allocated from an unprotected prior snapshot. Condition the append on ID availability and retry an actual collision.

### How to setup and perform the tests

1. Keep the reusable audit harness available on `fix/critical-ui-release-pass` in `/home/jakob/src/codex/bonsai`. The production branch intentionally contains only the reported fix. Docker images and generic test dependencies are already cached on this machine.
2. From that checkout, run:

```bash
python3 scripts/verify_minimal_prs.py --only RECOVERY-COMMENT-IDENTITIES
```

The harness extracts the candidate Git tree, so switching the running application checkout is unnecessary. Candidate checked: `34cbe08fed81255fd3d8d3d45b9763aabe5af934`.

### Expected outcome

Retain all texts with unique identifiers under forced simultaneous submissions.

Recorded result: 1 focused checks passed (api). Logs and source heads are pinned in the local verification ledger. Existing duplicate IDs are not renumbered by this fix.

### Additional context

- Finding: `RECOVERY-COMMENT-IDENTITIES`; apparent priority: P1.
- Repository: Bonsai; base: `development` (`21eccf7075fb59a897cb2ae86b0d6cdb95d0089c`).
- +15/-25 production lines in 1 file(s), relative to development.
- Git prerequisites: None.
- Paired repository candidate: None.
- Normal trigger: Comments submitted to one record at the same time can share an ID. Ordinary sequential comments do not trigger the collision.
- Selection assessment: Concurrency-dependent.
- Scope limit: Targeted fix; stated validation limits apply.

Publication is performed by the user when selected:

```bash
git -C /home/jakob/src/codex/bonsai push -u origin pr/recovery-comment-identities
```
