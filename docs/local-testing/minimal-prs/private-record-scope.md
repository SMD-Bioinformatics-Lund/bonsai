# Reject new private-marked records while sample ACLs are unfinished

An uninvited ordinary account can read an admin-owned private-marked record. The read function has no record-owner or visibility check. The candidate rejects new private-marked records, selecting a public-only creation contract. **This rejects new private creation only. Existing private-marked records are still readable across accounts; this is not an ACL implementation or a complete P0 closure.**

### How to setup and perform the tests

1. Keep the reusable audit harness available on `fix/critical-ui-release-pass` in `/home/jakob/src/codex/bonsai`. The production branch intentionally contains only the reported fix. Docker images and generic test dependencies are already cached on this machine.
2. From that checkout, run:

```bash
python3 scripts/verify_minimal_prs.py --only PRIVATE-RECORD-SCOPE
```

The harness extracts the candidate Git tree, so switching the running application checkout is unnecessary. Candidate checked: `ce4fa9e1779d0b3f08e3630520565ca3d01cd57e`.

### Expected outcome

Public record creation remains accepted and new private-marked creation returns 422 before the service is called.

Recorded result: 1 focused checks passed (api). Logs and source heads are pinned in the local verification ledger. Partial containment only: existing private-marked records remain exposed. A private-data deployment needs ACL enforcement or a separate migration/access decision; this branch alone does not close P0.

### Additional context

- Finding: `PRIVATE-RECORD-SCOPE`; apparent priority: P0.
- Repository: Bonsai; base: `development` (`21eccf7075fb59a897cb2ae86b0d6cdb95d0089c`).
- +2/-2 production lines in 1 file(s), relative to development.
- Git prerequisites: None.
- Paired repository candidate: None.
- Normal trigger: Public-default workflows are unaffected. Any private-marked record remains readable across accounts if this unfinished privacy feature is relied on.
- Selection assessment: Policy decision before release.
- Scope limit: Conditional containment; privacy P0 remains open for existing private data.

Publication is performed by the user when selected:

```bash
git -C /home/jakob/src/codex/bonsai push -u origin pr/private-record-scope
```
