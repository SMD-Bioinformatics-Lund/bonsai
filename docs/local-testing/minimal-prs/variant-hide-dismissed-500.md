# Read the stored rejection decision when filtering rows

The filter reads a legacy verified field before merging saved decisions. A record containing a rejected row returns HTTP 500. Merge saved decisions before filtering and read the existing rejection decision.

### How to setup and perform the tests

1. Keep the reusable audit harness available on `fix/critical-ui-release-pass` in `/home/jakob/src/codex/bonsai`. The production branch intentionally contains only the reported fix. Docker images and generic test dependencies are already cached on this machine.
2. From that checkout, run:

```bash
python3 scripts/verify_minimal_prs.py --only VARIANT-HIDE-DISMISSED-500
```

The harness extracts the candidate Git tree, so switching the running application checkout is unnecessary. Candidate checked: `20bbb27b2f85c82a25557aa2527f65f009c02019`.

### Expected outcome

Hide exactly the rejected rows using saved decision state, without changing stored decisions.

Recorded result: 1 focused checks passed (frontend). Logs and source heads are pinned in the local verification ledger. Read-only filtering is checked; stored decisions are not changed.

### Additional context

- Finding: `VARIANT-HIDE-DISMISSED-500`; apparent priority: P1.
- Repository: Bonsai; base: `development` (`21eccf7075fb59a897cb2ae86b0d6cdb95d0089c`).
- +2/-1 production lines in 1 file(s), relative to development.
- Git prerequisites: None.
- Paired repository candidate: None.
- Normal trigger: The option is enabled for stored rows using the current decision schema. The obsolete field lookup then fails.
- Selection assessment: Early review.
- Scope limit: Targeted fix; stated validation limits apply.
- Integration note: When combined with TB-NO-AMR-500, retain both the decision merge and the null-safe row lookup.

Publication is performed by the user when selected:

```bash
git -C /home/jakob/src/codex/bonsai push -u origin pr/variant-hide-dismissed-500
```
