# Group interleaved metadata categories without dropping fields

The view groups unsorted records by adjacent category, then overwrites a category when it appears again. Stored fields disappear from the rendered view. Sort by category before grouping the display fields.

### How to setup and perform the tests

1. Keep the reusable audit harness available on `fix/critical-ui-release-pass` in `/home/jakob/src/codex/bonsai`. The production branch intentionally contains only the reported fix. Docker images and generic test dependencies are already cached on this machine.
2. From that checkout, run:

```bash
python3 scripts/verify_minimal_prs.py --only METADATA-CATEGORY-LOSS
```

The harness extracts the candidate Git tree, so switching the running application checkout is unnecessary. Candidate checked: `13a4b49e3f6b50e8c717af6db068eb29d6a6273b`.

### Expected outcome

Display every field when categories are interleaved in stored order.

Recorded result: 1 focused checks passed (frontend). Logs and source heads are pinned in the local verification ledger. Only display grouping changes; stored field order and values remain untouched.

### Additional context

- Finding: `METADATA-CATEGORY-LOSS`; apparent priority: P1.
- Repository: Bonsai; base: `development` (`21eccf7075fb59a897cb2ae86b0d6cdb95d0089c`).
- +1/-1 production lines in 1 file(s), relative to development.
- Git prerequisites: None.
- Paired repository candidate: None.
- Normal trigger: Fields from a previously used category are appended after another category. Stored order then interleaves categories.
- Selection assessment: Early review.
- Scope limit: Targeted fix; stated validation limits apply.

Publication is performed by the user when selected:

```bash
git -C /home/jakob/src/codex/bonsai push -u origin pr/metadata-category-loss
```
