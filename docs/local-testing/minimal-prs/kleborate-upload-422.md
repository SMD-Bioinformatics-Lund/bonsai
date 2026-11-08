# Forward an optional hAMRonization companion through the API

Frozen reports parse offline with their companion, but the original four API attempts returned HTTP 422. The upload route exposes no hAMRonization companion input. Forward one optional multipart file through API/service and a paired SDK upload branch.

### How to setup and perform the tests

1. Keep the reusable audit harness available on `fix/critical-ui-release-pass` in `/home/jakob/src/codex/bonsai`. The production branch intentionally contains only the reported fix. Docker images and generic test dependencies are already cached on this machine.
2. From that checkout, run:

```bash
python3 scripts/verify_minimal_prs.py --only KLEBORATE-UPLOAD-422
```

The harness extracts the candidate Git tree, so switching the running application checkout is unnecessary. Candidate checked: `6547f49a7312aa1ba12eeeeccaa2be7e068b5ce7`.

### Expected outcome

Define and stub-test companion-file plumbing; verify ingestion separately before claiming the integration works.

Recorded result: 2 focused checks passed (api). Logs and source heads are pinned in the local verification ledger. The app and SDK branches are a pair. Transport and stream binding are stub-tested; live parsing, persistence and end-to-end ingestion remain unverified.

### Additional context

- Finding: `KLEBORATE-UPLOAD-422`; apparent priority: P1.
- Repository: Bonsai; base: `development` (`21eccf7075fb59a897cb2ae86b0d6cdb95d0089c`).
- +5/-0 production lines in 2 file(s), relative to development.
- Git prerequisites: None.
- Paired repository candidate: KLEBORATE-CLIENT-COMPANION.
- Normal trigger: A Kleborate report requires its hAMRonization companion, but the current route/client cannot provide it. Actual local uploader usage is unknown.
- Selection assessment: Feature-dependent.
- Scope limit: Targeted fix; stated validation limits apply.
- Operational authorization prerequisite: `pr/account-role-permissions` then `pr/analysis-upload-role-gate` for the dedicated uploader role. Live ingestion has not been performed.

Publication is performed by the user when selected:

```bash
git -C /home/jakob/src/codex/bonsai push -u origin pr/kleborate-upload-422
```
