# Intersect numeric row-filter predicates

Depth filtering replaces the prior frequency result instead of combining it. Three rows remain when the requested conjunction should return none. Combine each depth predicate with the existing accumulated filter result.

### How to setup and perform the tests

1. Keep the reusable audit harness available on `fix/critical-ui-release-pass` in `/home/jakob/src/codex/bonsai`. The production branch intentionally contains only the reported fix. Docker images and generic test dependencies are already cached on this machine.
2. From that checkout, run:

```bash
python3 scripts/verify_minimal_prs.py --only VARIANT-FILTER-AND
```

The harness extracts the candidate Git tree, so switching the running application checkout is unnecessary. Candidate checked: `16fb3d32d5b9694365c3880eb2cb63b05eb08e5e`.

### Expected outcome

Both predicates must intersect, including cases where either one fails.

Recorded result: 3 focused checks passed (frontend). Logs and source heads are pinned in the local verification ledger. Only Boolean filter composition changes.

### Additional context

- Finding: `VARIANT-FILTER-AND`; apparent priority: P1.
- Repository: Bonsai; base: `development` (`21eccf7075fb59a897cb2ae86b0d6cdb95d0089c`).
- +2/-2 production lines in 1 file(s), relative to development.
- Git prerequisites: None.
- Paired repository candidate: None.
- Normal trigger: Both numeric predicates are enabled and a row passes only the second. Using one predicate does not expose the overwritten result.
- Selection assessment: Early review.
- Scope limit: Targeted fix; stated validation limits apply.

Publication is performed by the user when selected:

```bash
git -C /home/jakob/src/codex/bonsai push -u origin pr/variant-filter-and
```
