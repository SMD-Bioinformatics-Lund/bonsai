# Send the optional hAMRonization file in SDK multipart uploads

The SDK cannot supply the companion file accepted by the paired API change. Add one optional input path and bind it as a multipart file; close both file handles.

### How to setup and perform the tests

1. Keep the reusable audit harness available on `fix/critical-ui-release-pass` in `/home/jakob/src/codex/bonsai`. The production branch intentionally contains only the reported fix. Docker images and generic test dependencies are already cached on this machine.
2. From that checkout, run:

```bash
python3 scripts/verify_minimal_prs.py --only KLEBORATE-CLIENT-COMPANION
```

The harness extracts the candidate Git tree, so switching the running application checkout is unnecessary. Candidate checked: `e9c6d609da6a2c4c7c447026a71df8973c1cf78b`.

### Expected outcome

Both files are sent as multipart parts and both handles close after the request.

Recorded result: 1 focused checks passed (sdk). Logs and source heads are pinned in the local verification ledger. The app and SDK branches are a pair. Transport and stream binding are stub-tested; live parsing, persistence and end-to-end ingestion remain unverified.

### Additional context

- Finding: `KLEBORATE-CLIENT-COMPANION`; apparent priority: P1.
- Repository: SDK; base: `master` (`5789a9c7530407683f1fee9ffa450512269e62bc`).
- +3/-2 production lines in 2 file(s), relative to master.
- Git prerequisites: None.
- Paired repository candidate: KLEBORATE-UPLOAD-422.
- Normal trigger: A Kleborate report requires its hAMRonization companion, but the current route/client cannot provide it. Actual local uploader usage is unknown.
- Selection assessment: Feature-dependent.
- Scope limit: Targeted fix; stated validation limits apply.
- Operational authorization prerequisite: `pr/account-role-permissions` then `pr/analysis-upload-role-gate` for the dedicated uploader role. Live ingestion has not been performed.

Publication is performed by the user when selected:

```bash
git -C /home/jakob/src/codex/bonsai/bonsai-sdk push -u origin pr/kleborate-client-companion
```
