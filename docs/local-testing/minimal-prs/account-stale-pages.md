# Revalidate restored pages after account changes

After logout or account switching, other tabs and browser history can retain the prior rendered page and access token. Independent profiles are a separate case. Revalidate restored pages and reload on a cross-tab account change.

### How to setup and perform the tests

1. Keep the reusable audit harness available on `fix/critical-ui-release-pass` in `/home/jakob/src/codex/bonsai`. The production branch intentionally contains only the reported fix. Docker images and generic test dependencies are already cached on this machine.
2. From that checkout, run:

```bash
python3 scripts/verify_minimal_prs.py --only ACCOUNT-STALE-PAGES
```

The harness extracts the candidate Git tree, so switching the running application checkout is unnecessary. Candidate checked: `8567eda7b11457fa7619fc9fe30f7e21d0ba14ad`.

### Expected outcome

Revalidate restored pages and coordinate account changes across tabs. Server-side token revocation is a separate contract.

Recorded result: 3 focused checks passed (node). Logs and source heads are pinned in the local verification ledger. This refreshes visible pages; it does not provide server-side JWT revocation or per-account basket storage.

### Additional context

- Finding: `ACCOUNT-STALE-PAGES`; apparent priority: P1.
- Repository: Bonsai; base: `development` (`21eccf7075fb59a897cb2ae86b0d6cdb95d0089c`).
- +15/-0 production lines in 1 file(s), relative to development.
- Git prerequisites: None.
- Paired repository candidate: None.
- Normal trigger: Accounts are switched or logged out with old tabs/history still available in the same browser profile. Separate profiles reduce exposure.
- Selection assessment: Environment-dependent.
- Scope limit: Targeted fix; stated validation limits apply.

Publication is performed by the user when selected:

```bash
git -C /home/jakob/src/codex/bonsai push -u origin pr/account-stale-pages
```
