# Open typed account responses and preserve profile update semantics

The edit form indexes a typed UserResponse as a dictionary. Opening an existing account returns HTTP 500. Read typed response attributes and preserve password/update return semantics.

### How to setup and perform the tests

1. Keep the reusable audit harness available on `fix/critical-ui-release-pass` in `/home/jakob/src/codex/bonsai`. The production branch intentionally contains only the reported fix. Docker images and generic test dependencies are already cached on this machine.
2. From that checkout, run:

```bash
python3 scripts/verify_minimal_prs.py --only ADMIN-EDIT-USER-500
```

The harness extracts the candidate Git tree, so switching the running application checkout is unnecessary. Candidate checked: `619cab28e4bf8f8706a391804b017442090106aa`.

### Expected outcome

Populate the form from the typed response and verify that an ordinary profile edit persists.

Recorded result: 2 focused checks passed (frontend, api). Logs and source heads are pinned in the local verification ledger. The UI and API changes are kept together because opening and saving form one workflow.

### Additional context

- Finding: `ADMIN-EDIT-USER-500`; apparent priority: P1.
- Repository: Bonsai; base: `development` (`21eccf7075fb59a897cb2ae86b0d6cdb95d0089c`).
- +7/-8 production lines in 2 file(s), relative to development.
- Git prerequisites: None.
- Paired repository candidate: None.
- Normal trigger: An administrator opens or updates an existing local account. External-account management may avoid this path.
- Selection assessment: Feature-dependent.
- Scope limit: Targeted fix; stated validation limits apply.

Publication is performed by the user when selected:

```bash
git -C /home/jakob/src/codex/bonsai push -u origin pr/admin-edit-user-500
```
