# Render accepted metadata table shapes consistently

CSV-shaped metadata can be accepted and stored without conversion to the table read shape. The page then shows no columns or rows. Normalize the accepted read shapes and render their headings and rows.

### How to setup and perform the tests

1. Keep the reusable audit harness available on `fix/critical-ui-release-pass` in `/home/jakob/src/codex/bonsai`. The production branch intentionally contains only the reported fix. Docker images and generic test dependencies are already cached on this machine.
2. From that checkout, run:

```bash
python3 scripts/verify_minimal_prs.py --only METADATA-TABLE-EMPTY
```

The harness extracts the candidate Git tree, so switching the running application checkout is unnecessary. Candidate checked: `fa643f1d987e4b90a25f3bcd530581c19651e44e`.

### Expected outcome

Show original headings and cells for both accepted CSV-shaped and stored-table representations.

Recorded result: 3 focused checks passed (api, frontend). Logs and source heads are pinned in the local verification ledger. Three files cover the model/read boundary and template; this is larger than the single-line display fixes.

### Additional context

- Finding: `METADATA-TABLE-EMPTY`; apparent priority: P1.
- Repository: Bonsai; base: `development` (`21eccf7075fb59a897cb2ae86b0d6cdb95d0089c`).
- +21/-7 production lines in 3 file(s), relative to development.
- Git prerequisites: None.
- Paired repository candidate: None.
- Normal trigger: An accepted metadata table is opened in the summary or standalone table view. Frequency depends on whether table metadata is used locally.
- Selection assessment: Feature-dependent.
- Scope limit: Targeted fix; stated validation limits apply.
- Integration note: When combined with CSV-EMPTY-CELL-500, union the pydantic imports (BeforeValidator and field_validator).

Publication is performed by the user when selected:

```bash
git -C /home/jakob/src/codex/bonsai push -u origin pr/metadata-table-empty
```
