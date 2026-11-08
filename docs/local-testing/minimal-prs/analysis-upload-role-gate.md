# Require write permission for analysis uploads

The real baseline router admits user and rejects uploader in an isolated authorization test: observed statuses 201 and 401 respectively. The downstream service is a stub. Change the upload route to the existing write scope, after repairing shared role checks.

### How to setup and perform the tests

1. Keep the reusable audit harness available on `fix/critical-ui-release-pass` in `/home/jakob/src/codex/bonsai`. The production branch intentionally contains only the reported fix. Docker images and generic test dependencies are already cached on this machine.
2. From that checkout, run:

```bash
python3 scripts/verify_minimal_prs.py --only ANALYSIS-UPLOAD-ROLE-GATE
```

The harness extracts the candidate Git tree, so switching the running application checkout is unnecessary. Candidate checked: `dd5c2481be225712b0b4ae0565d7b701b4c4686e`.

### Expected outcome

Require the intended write scope and verify the complete role matrix without executing ingestion.

Recorded result: 3 focused checks passed (permission). Logs and source heads are pinned in the local verification ledger. Requires ACCOUNT-ROLE-PERMISSIONS. Authorization was tested with the downstream service stubbed.

### Additional context

- Finding: `ANALYSIS-UPLOAD-ROLE-GATE`; apparent priority: P0.
- Repository: Bonsai; base: `pr/account-role-permissions` (`5b7e90594dde4b4b514eef8d45db46162da499ea`).
- +1/-1 production lines in 1 file(s), relative to pr/account-role-permissions.
- Git prerequisites: ACCOUNT-ROLE-PERMISSIONS.
- Paired repository candidate: None.
- Normal trigger: Every dedicated-uploader submission is denied; ordinary-account submissions are admitted. Exposure depends on which role the ingestion client uses.
- Selection assessment: Early review.
- Scope limit: Targeted fix; stated validation limits apply.

Publication is performed by the user when selected:

```bash
git -C /home/jakob/src/codex/bonsai push -u origin pr/analysis-upload-role-gate
```
