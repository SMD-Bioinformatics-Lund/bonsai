# Batch membership lookups within the API query limit

The UI sends one membership lookup for 125 selected records while the API permits at most 100 IDs. The common group is not preselected. Batch membership reads within the API limit while retaining common-group calculation.

### How to setup and perform the tests

1. Keep the reusable audit harness available on `fix/critical-ui-release-pass` in `/home/jakob/src/codex/bonsai`. The production branch intentionally contains only the reported fix. Docker images and generic test dependencies are already cached on this machine.
2. From that checkout, run:

```bash
python3 scripts/verify_minimal_prs.py --only GROUP-MEMBERSHIP-LIMIT
```

The harness extracts the candidate Git tree, so switching the running application checkout is unnecessary. Candidate checked: `6ddfd15b2c4f9c439ec561999b56fa4aea73d1a8`.

### Expected outcome

Batch membership reads within the API limit and preselect the common group for all 125 records.

Recorded result: 2 focused checks passed (node). Logs and source heads are pinned in the local verification ledger. A 125-record generic selection was checked; this does not resolve partial write batches.

### Additional context

- Finding: `GROUP-MEMBERSHIP-LIMIT`; apparent priority: P1.
- Repository: Bonsai; base: `development` (`21eccf7075fb59a897cb2ae86b0d6cdb95d0089c`).
- +8/-7 production lines in 1 file(s), relative to development.
- Git prerequisites: None.
- Paired repository candidate: None.
- Normal trigger: More than 100 records are selected for group management. Smaller selections do not hit the membership query limit.
- Selection assessment: Feature-dependent.
- Scope limit: Targeted fix; stated validation limits apply.

Publication is performed by the user when selected:

```bash
git -C /home/jakob/src/codex/bonsai push -u origin pr/group-membership-limit
```
