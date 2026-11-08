# Require write permission for record deletion

Both single and bulk API deletion use update permission, which ordinary accounts hold. The UI does not offer them deletion. Use the existing write permission on both deletion routes.

### How to setup and perform the tests

1. Keep the reusable audit harness available on `fix/critical-ui-release-pass` in `/home/jakob/src/codex/bonsai`. The production branch intentionally contains only the reported fix. Docker images and generic test dependencies are already cached on this machine.
2. From that checkout, run:

```bash
python3 scripts/verify_minimal_prs.py --only ORDINARY-RECORD-DELETE
```

The harness extracts the candidate Git tree, so switching the running application checkout is unnecessary. Candidate checked: `e07c608476803971b48e980fe1ffb318a2f2db0a`.

### Expected outcome

Deny ordinary deletion before any service call; retain administrator deletion.

Recorded result: 4 focused checks passed (api). Logs and source heads are pinned in the local verification ledger. Destructive permission boundary; verify ordinary denial and administrator access before release.

### Additional context

- Finding: `ORDINARY-RECORD-DELETE`; apparent priority: P0.
- Repository: Bonsai; base: `development` (`21eccf7075fb59a897cb2ae86b0d6cdb95d0089c`).
- +2/-2 production lines in 1 file(s), relative to development.
- Git prerequisites: None.
- Paired repository candidate: None.
- Normal trigger: An ordinary account using the delete API is affected every time. The ordinary UI hides deletion, so accidental normal UI use is less likely.
- Selection assessment: Early review.
- Scope limit: Targeted fix; stated validation limits apply.

Publication is performed by the user when selected:

```bash
git -C /home/jakob/src/codex/bonsai push -u origin pr/ordinary-record-delete
```
