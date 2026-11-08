# Redraw selected-only tables after selection changes

After Select all, Show only selected and Deselect all, old rows remain visible. The later file check exported eight records with zero selected. Redraw the shared table after selection changes.

### How to setup and perform the tests

1. Keep the reusable audit harness available on `fix/critical-ui-release-pass` in `/home/jakob/src/codex/bonsai`. The production branch intentionally contains only the reported fix. Docker images and generic test dependencies are already cached on this machine.
2. From that checkout, run:

```bash
/home/jakob/data/codex/bonsai/environments/release-test/bin/python scripts/check_minimal_pr_browser.py
```

The harness extracts the candidate Git tree, so switching the running application checkout is unnecessary. Candidate checked: `859f603e8db62593a71518b29a35e1bf11917a2c`.

### Expected outcome

At zero and nonzero selections, displayed rows and exported records must match the selected-only view.

Recorded result: 4 focused checks passed (Chromium / real DataTables plugins). Logs and source heads are pinned in the local verification ledger. The shared handler also covers ordinary accounts without administrator group controls.

### Additional context

- Finding: `SELECTED-FILTER-STALE`; apparent priority: P1.
- Repository: Bonsai; base: `development` (`21eccf7075fb59a897cb2ae86b0d6cdb95d0089c`).
- +1/-0 production lines in 1 file(s), relative to development.
- Git prerequisites: None.
- Paired repository candidate: None.
- Normal trigger: Show selected is active and the last selected row is cleared. The stale display also contaminates the subsequent CSV export.
- Selection assessment: Early review.
- Scope limit: Targeted fix; stated validation limits apply.

Publication is performed by the user when selected:

```bash
git -C /home/jakob/src/codex/bonsai push -u origin pr/selected-filter-stale
```
