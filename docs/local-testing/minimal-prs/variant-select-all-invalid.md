# Restrict bulk row selection to identified checkboxes

A three-row table creates four local payload entries, including one without valid identifiers. The header checkbox is also handled as a row checkbox. Bind selection only to checkboxes carrying a row identifier.

### How to setup and perform the tests

1. Keep the reusable audit harness available on `fix/critical-ui-release-pass` in `/home/jakob/src/codex/bonsai`. The production branch intentionally contains only the reported fix. Docker images and generic test dependencies are already cached on this machine.
2. From that checkout, run:

```bash
/home/jakob/data/codex/bonsai/environments/release-test/bin/python scripts/check_minimal_pr_browser.py
```

The harness extracts the candidate Git tree, so switching the running application checkout is unnecessary. Candidate checked: `6d08d7abd5256440ad9f0c74b25e77b7c0ac5b5a`.

### Expected outcome

The header must select exactly the displayed valid row IDs, including after filtering; no write is needed for this check.

Recorded result: 4 focused checks passed (Chromium / real DataTables plugins). Logs and source heads are pinned in the local verification ledger. Selection payloads were checked without submitting any action.

### Additional context

- Finding: `VARIANT-SELECT-ALL-INVALID`; apparent priority: P1.
- Repository: Bonsai; base: `development` (`21eccf7075fb59a897cb2ae86b0d6cdb95d0089c`).
- +2/-2 production lines in 1 file(s), relative to development.
- Git prerequisites: None.
- Paired repository candidate: None.
- Normal trigger: The header checkbox is clicked in the stored-row table, including after a table filter. Individual row clicks avoid the extra target.
- Selection assessment: Early review.
- Scope limit: Targeted fix; stated validation limits apply.

Publication is performed by the user when selected:

```bash
git -C /home/jakob/src/codex/bonsai push -u origin pr/variant-select-all-invalid
```
