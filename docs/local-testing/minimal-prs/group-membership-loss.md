# Preserve individual memberships when applying common groups

The selector displays common memberships, then treats them as each record's complete target set. Applying unchanged settings removes individual memberships. Remove only originally common groups and capture the selection used by Apply.

### How to setup and perform the tests

1. Keep the reusable audit harness available on `fix/critical-ui-release-pass` in `/home/jakob/src/codex/bonsai`. The production branch intentionally contains only the reported fix. Docker images and generic test dependencies are already cached on this machine.
2. From that checkout, run:

```bash
python3 scripts/verify_minimal_prs.py --only GROUP-MEMBERSHIP-LOSS
```

The harness extracts the candidate Git tree, so switching the running application checkout is unnecessary. Candidate checked: `0e782307e2551a6c3afad00b5595bb6417e9624f`.

### Expected outcome

Apply the unchanged common selection and preserve every record's individual memberships.

Recorded result: 4 focused checks passed (node). Logs and source heads are pinned in the local verification ledger. No component redesign or partial-batch recovery is included.

### Additional context

- Finding: `GROUP-MEMBERSHIP-LOSS`; apparent priority: P1.
- Repository: Bonsai; base: `development` (`21eccf7075fb59a897cb2ae86b0d6cdb95d0089c`).
- +7/-2 production lines in 1 file(s), relative to development.
- Git prerequisites: None.
- Paired repository candidate: None.
- Normal trigger: Applying an unchanged common group selection erases individual memberships when the selected records have different groups.
- Selection assessment: Early review.
- Scope limit: Targeted fix; stated validation limits apply.

Publication is performed by the user when selected:

```bash
git -C /home/jakob/src/codex/bonsai push -u origin pr/group-membership-loss
```
