# Apply route-specific role scopes to generic create and read

The shared active-user dependency adds users:me to write-only uploader requests. The older list route requires write permission from ordinary readers. Remove the unrelated shared scope and retain explicit per-route scopes.

### How to setup and perform the tests

1. Keep the reusable audit harness available on `fix/critical-ui-release-pass` in `/home/jakob/src/codex/bonsai`. The production branch intentionally contains only the reported fix. Docker images and generic test dependencies are already cached on this machine.
2. From that checkout, run:

```bash
python3 scripts/verify_minimal_prs.py --only ACCOUNT-ROLE-PERMISSIONS
```

The harness extracts the candidate Git tree, so switching the running application checkout is unnecessary. Candidate checked: `5b7e90594dde4b4b514eef8d45db46162da499ea`.

### Expected outcome

Allow generic uploader creation and ordinary list reads while preserving the intended denials.

Recorded result: 5 focused checks passed (api). Logs and source heads are pinned in the local verification ledger. This is the prerequisite for the one-line upload boundary fix.

### Additional context

- Finding: `ACCOUNT-ROLE-PERMISSIONS`; apparent priority: P1.
- Repository: Bonsai; base: `development` (`21eccf7075fb59a897cb2ae86b0d6cdb95d0089c`).
- +9/-9 production lines in 3 file(s), relative to development.
- Git prerequisites: None.
- Paired repository candidate: None.
- Normal trigger: A dedicated uploader creates a generic record, or an ordinary user uses the legacy list endpoint. The frontend's summary list takes another path.
- Selection assessment: Early review.
- Scope limit: Targeted fix; stated validation limits apply.

Publication is performed by the user when selected:

```bash
git -C /home/jakob/src/codex/bonsai push -u origin pr/account-role-permissions
```
