# Use plain QC status values for SearchBuilder filtering

The status column is filterable but excluded from the search cache used by the advanced filter. A known matching row is omitted. Provide the plain status search value and the SearchBuilder orthogonal mapping.

### How to setup and perform the tests

1. Keep the reusable audit harness available on `fix/critical-ui-release-pass` in `/home/jakob/src/codex/bonsai`. The production branch intentionally contains only the reported fix. Docker images and generic test dependencies are already cached on this machine.
2. From that checkout, run:

```bash
/home/jakob/data/codex/bonsai/environments/release-test/bin/python scripts/check_minimal_pr_browser.py
```

The harness extracts the candidate Git tree, so switching the running application checkout is unnecessary. Candidate checked: `77b75326f97936382633c001a9ee7a562b48a824`.

### Expected outcome

Exact and combined status filters must return all expected records; clearing them must restore the full table.

Recorded result: 4 focused checks passed (Chromium / real DataTables plugins). Logs and source heads are pinned in the local verification ledger. Real DataTables checks cover exact filtering, combined conditions, clearing and export data.

### Additional context

- Finding: `QC-FILTER-EMPTY`; apparent priority: P1.
- Repository: Bonsai; base: `development` (`21eccf7075fb59a897cb2ae86b0d6cdb95d0089c`).
- +7/-1 production lines in 2 file(s), relative to development.
- Git prerequisites: None.
- Paired repository candidate: None.
- Normal trigger: SearchBuilder filters QC exactly while that column is excluded from global search. The normal overview column configuration has this combination.
- Selection assessment: Early review.
- Scope limit: Targeted fix; stated validation limits apply.

Publication is performed by the user when selected:

```bash
git -C /home/jakob/src/codex/bonsai push -u origin pr/qc-filter-empty
```
