# Render decisions without optional display metadata

The stored summary indexes optional resistance-level metadata that is absent in a valid stored decision. Rendering returns HTTP 500. Read the optional display metadata before rendering its label.

### How to setup and perform the tests

1. Keep the reusable audit harness available on `fix/critical-ui-release-pass` in `/home/jakob/src/codex/bonsai`. The production branch intentionally contains only the reported fix. Docker images and generic test dependencies are already cached on this machine.
2. From that checkout, run:

```bash
python3 scripts/verify_minimal_prs.py --only TB-CURATION-500
```

The harness extracts the candidate Git tree, so switching the running application checkout is unnecessary. Candidate checked: `d2218de5ec04515bdc642ab509f902dbc397be5f`.

### Expected outcome

Render the original summary and decisions when optional display fields are missing.

Recorded result: 3 focused checks passed (frontend). Logs and source heads are pinned in the local verification ledger. Literal stored display values are checked, without making or changing a diagnostic decision.

### Additional context

- Finding: `TB-CURATION-500`; apparent priority: P1.
- Repository: Bonsai; base: `development` (`21eccf7075fb59a897cb2ae86b0d6cdb95d0089c`).
- +3/-1 production lines in 1 file(s), relative to development.
- Git prerequisites: None.
- Paired repository candidate: None.
- Normal trigger: A stored decision lacks optional display metadata. Presence depends on the producer and editing path; populated metadata avoids the crash.
- Selection assessment: Early review.
- Scope limit: Targeted fix; stated validation limits apply.

Publication is performed by the user when selected:

```bash
git -C /home/jakob/src/codex/bonsai push -u origin pr/tb-curation-500
```
