# Append metadata atomically without overwriting concurrent fields

Two isolated baseline appends both return success, but only one field remains. The read-modify-write operation replaces the complete metadata array. Append atomically with a field-name condition and distinguish duplicate conflicts.

### How to setup and perform the tests

1. Keep the reusable audit harness available on `fix/critical-ui-release-pass` in `/home/jakob/src/codex/bonsai`. The production branch intentionally contains only the reported fix. Docker images and generic test dependencies are already cached on this machine.
2. From that checkout, run:

```bash
python3 scripts/verify_minimal_prs.py --only RECOVERY-METADATA-LOSS
```

The harness extracts the candidate Git tree, so switching the running application checkout is unnecessary. Candidate checked: `d7ee2464e82811107129ca462acd6cb6189d4603`.

### Expected outcome

Retain all independent concurrent fields; concurrent creation of one field must have one winner.

Recorded result: 2 focused checks passed (api). Logs and source heads are pinned in the local verification ledger. Requires METADATA-ADD-500. Independent fields and competing duplicate fields were checked under forced overlap.

### Additional context

- Finding: `RECOVERY-METADATA-LOSS`; apparent priority: P1.
- Repository: Bonsai; base: `pr/metadata-add-500` (`e767620b6d62b0dcbb9530147461280e22a7fbef`).
- +5/-6 production lines in 1 file(s), relative to pr/metadata-add-500.
- Git prerequisites: METADATA-ADD-500.
- Paired repository candidate: None.
- Normal trigger: Two users or automated clients append fields to the same record before either save completes. Less likely in a single-editor manual workflow.
- Selection assessment: Concurrency-dependent.
- Scope limit: Targeted fix; stated validation limits apply.

Publication is performed by the user when selected:

```bash
git -C /home/jakob/src/codex/bonsai push -u origin pr/recovery-metadata-loss
```
