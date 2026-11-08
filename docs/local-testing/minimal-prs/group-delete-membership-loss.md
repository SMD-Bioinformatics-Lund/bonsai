# Limit group deletion to the target membership edges

Deleting one group removes a member's links to other groups. The record itself remains; membership aggregation returns edges outside the requested group. Match the target group after unwinding membership arrays.

### How to setup and perform the tests

1. Keep the reusable audit harness available on `fix/critical-ui-release-pass` in `/home/jakob/src/codex/bonsai`. The production branch intentionally contains only the reported fix. Docker images and generic test dependencies are already cached on this machine.
2. From that checkout, run:

```bash
python3 scripts/verify_minimal_prs.py --only GROUP-DELETE-MEMBERSHIP-LOSS
```

The harness extracts the candidate Git tree, so switching the running application checkout is unnecessary. Candidate checked: `5861b369bc71470a980ae4aed3911937df109fb7`.

### Expected outcome

Delete a populated group while retaining all records and every unrelated membership edge.

Recorded result: 1 focused checks passed (api). Logs and source heads are pinned in the local verification ledger. A one-stage query fix prevents unrelated membership deletion.

### Additional context

- Finding: `GROUP-DELETE-MEMBERSHIP-LOSS`; apparent priority: P1.
- Repository: Bonsai; base: `development` (`21eccf7075fb59a897cb2ae86b0d6cdb95d0089c`).
- +1/-0 production lines in 1 file(s), relative to development.
- Git prerequisites: None.
- Paired repository candidate: None.
- Normal trigger: Deleting a populated group removes other memberships when records belong to multiple groups. Overlapping cohorts make this a realistic administrative trigger.
- Selection assessment: Early review.
- Scope limit: Targeted fix; stated validation limits apply.

Publication is performed by the user when selected:

```bash
git -C /home/jakob/src/codex/bonsai push -u origin pr/group-delete-membership-loss
```
