# Normalize missing numeric CSV cells to empty text

The baseline CSV reader retains a non-finite numeric value for an empty inventory cell. JSON serialization raises Out of range float values are not JSON compliant. Normalize missing numeric cells to empty text in the stored table model.

### How to setup and perform the tests

1. Keep the reusable audit harness available on `fix/critical-ui-release-pass` in `/home/jakob/src/codex/bonsai`. The production branch intentionally contains only the reported fix. Docker images and generic test dependencies are already cached on this machine.
2. From that checkout, run:

```bash
python3 scripts/verify_minimal_prs.py --only CSV-EMPTY-CELL-500
```

The harness extracts the candidate Git tree, so switching the running application checkout is unnecessary. Candidate checked: `9811fa547b554c5b5dee2e6e742bca8d2b0deb2f`.

### Expected outcome

Accept missing cells and render the stored table without a serialization error.

Recorded result: 1 focused checks passed (api). Logs and source heads are pinned in the local verification ledger. The patch handles the reported missing-cell case; unrelated malformed numeric input is excluded.

### Additional context

- Finding: `CSV-EMPTY-CELL-500`; apparent priority: P1.
- Repository: Bonsai; base: `development` (`21eccf7075fb59a897cb2ae86b0d6cdb95d0089c`).
- +7/-1 production lines in 1 file(s), relative to development.
- Git prerequisites: None.
- Paired repository candidate: None.
- Normal trigger: A CSV has a blank cell in a column inferred as numeric. Such blanks are ordinary inventory/metadata input, if CSV tables are used.
- Selection assessment: Early review.
- Scope limit: Targeted fix; stated validation limits apply.
- Integration note: When combined with METADATA-TABLE-EMPTY, union the pydantic imports (BeforeValidator and field_validator).

Publication is performed by the user when selected:

```bash
git -C /home/jakob/src/codex/bonsai push -u origin pr/csv-empty-cell-500
```
