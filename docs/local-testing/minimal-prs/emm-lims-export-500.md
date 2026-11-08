# Read current EMM descriptors in CSV and TSV formatters

The formatter accesses the old descriptor field and old result-type name. Positive and empty EMM exports return HTTP 500 instead of a file. Read the typed descriptor and its dictionary fields, including the defined empty case.

### How to setup and perform the tests

1. Keep the reusable audit harness available on `fix/critical-ui-release-pass` in `/home/jakob/src/codex/bonsai`. The production branch intentionally contains only the reported fix. Docker images and generic test dependencies are already cached on this machine.
2. From that checkout, run:

```bash
python3 scripts/verify_minimal_prs.py --only EMM-LIMS-EXPORT-500
```

The harness extracts the candidate Git tree, so switching the running application checkout is unnecessary. Candidate checked: `3aeb54797bab82ed33fc78ef7ee190bfbe3a78e1`.

### Expected outcome

Produce CSV and TSV with correct record identity and supplied values, including defined empty results.

Recorded result: 5 focused checks passed (api). Logs and source heads are pinned in the local verification ledger. CSV/TSV identity and literal supplied values are tested.

### Additional context

- Finding: `EMM-LIMS-EXPORT-500`; apparent priority: P1.
- Repository: Bonsai; base: `development` (`21eccf7075fb59a897cb2ae86b0d6cdb95d0089c`).
- +5/-2 production lines in 1 file(s), relative to development.
- Git prerequisites: None.
- Paired repository candidate: None.
- Normal trigger: The configured EMM export is requested for current positive or empty descriptors. Other export categories use different formatters.
- Selection assessment: Feature-dependent.
- Scope limit: Targeted fix; stated validation limits apply.

Publication is performed by the user when selected:

```bash
git -C /home/jakob/src/codex/bonsai push -u origin pr/emm-lims-export-500
```
