# Append typed metadata alongside existing stored fields

Appending to a record with existing metadata mixes raw dictionaries and typed entries. Normal input fails instead of being appended. Keep stored records as dictionaries and serialize only new typed fields.

### How to setup and perform the tests

1. Keep the reusable audit harness available on `fix/critical-ui-release-pass` in `/home/jakob/src/codex/bonsai`. The production branch intentionally contains only the reported fix. Docker images and generic test dependencies are already cached on this machine.
2. From that checkout, run:

```bash
python3 scripts/verify_minimal_prs.py --only METADATA-ADD-500
```

The harness extracts the candidate Git tree, so switching the running application checkout is unnecessary. Candidate checked: `e767620b6d62b0dcbb9530147461280e22a7fbef`.

### Expected outcome

Append valid fields while retaining originals; duplicate fields must get clear conflict feedback.

Recorded result: 2 focused checks passed (api). Logs and source heads are pinned in the local verification ledger. Concurrent append safety is a separate dependent candidate.

### Additional context

- Finding: `METADATA-ADD-500`; apparent priority: P1.
- Repository: Bonsai; base: `development` (`21eccf7075fb59a897cb2ae86b0d6cdb95d0089c`).
- +6/-6 production lines in 1 file(s), relative to development.
- Git prerequisites: None.
- Paired repository candidate: None.
- Normal trigger: Appending to a record with existing metadata reaches the broken dictionary/object mix. A first append to an empty record may succeed.
- Selection assessment: Early review.
- Scope limit: Targeted fix; stated validation limits apply.

Publication is performed by the user when selected:

```bash
git -C /home/jakob/src/codex/bonsai push -u origin pr/metadata-add-500
```
