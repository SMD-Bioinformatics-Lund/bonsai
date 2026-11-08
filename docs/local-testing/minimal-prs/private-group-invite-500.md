# Use consistent account shapes for private-group invitees

Creation accesses a nonexistent owner_id attribute. Group listing and direct lookup also apply a public-only visibility helper instead of honoring owner/invitee access. Use the existing account response and membership helpers consistently.

### How to setup and perform the tests

1. Keep the reusable audit harness available on `fix/critical-ui-release-pass` in `/home/jakob/src/codex/bonsai`. The production branch intentionally contains only the reported fix. Docker images and generic test dependencies are already cached on this machine.
2. From that checkout, run:

```bash
python3 scripts/verify_minimal_prs.py --only PRIVATE-GROUP-INVITE-500
```

The harness extracts the candidate Git tree, so switching the running application checkout is unnecessary. Candidate checked: `1b1d4b7e97c6b02bd54d5990c93bca743b879e3b`.

### Expected outcome

Owner and invitees must create, list and open the group; an uninvited account must be denied.

Recorded result: 4 focused checks passed (api). Logs and source heads are pinned in the local verification ledger. Group access checks remain distinct from the unfinished private-record ACL feature.

### Additional context

- Finding: `PRIVATE-GROUP-INVITE-500`; apparent priority: P1.
- Repository: Bonsai; base: `development` (`21eccf7075fb59a897cb2ae86b0d6cdb95d0089c`).
- +3/-3 production lines in 2 file(s), relative to development.
- Git prerequisites: None.
- Paired repository candidate: None.
- Normal trigger: A private group is created with invited accounts. Public groups and owner-only groups do not trigger the same response-shape error.
- Selection assessment: Feature-dependent.
- Scope limit: Targeted fix; stated validation limits apply.

Publication is performed by the user when selected:

```bash
git -C /home/jakob/src/codex/bonsai push -u origin pr/private-group-invite-500
```
