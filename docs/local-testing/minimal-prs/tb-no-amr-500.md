# Keep summary and detail available for null stored results

A valid null result is indexed as a dictionary in several reading helpers. Empty-result records cannot be opened reliably. Keep null envelopes out of row traversal and render explicit availability text.

### How to setup and perform the tests

1. Keep the reusable audit harness available on `fix/critical-ui-release-pass` in `/home/jakob/src/codex/bonsai`. The production branch intentionally contains only the reported fix. Docker images and generic test dependencies are already cached on this machine.
2. From that checkout, run:

```bash
python3 scripts/verify_minimal_prs.py --only TB-NO-AMR-500
```

The harness extracts the candidate Git tree, so switching the running application checkout is unnecessary. Candidate checked: `e6d57246675b3a8b91de544d67792b4e9e0197c2`.

### Expected outcome

Keep stored null values and provide explicit availability feedback throughout both views.

Recorded result: 3 focused checks passed (frontend). Logs and source heads are pinned in the local verification ledger. Four files cover both views and shared readers; source data stays null.

### Additional context

- Finding: `TB-NO-AMR-500`; apparent priority: P1.
- Repository: Bonsai; base: `development` (`21eccf7075fb59a897cb2ae86b0d6cdb95d0089c`).
- +14/-7 production lines in 4 file(s), relative to development.
- Git prerequisites: None.
- Paired repository candidate: None.
- Normal trigger: A stored report envelope has a null result and its summary or detail is opened. Normal fully populated results do not trigger this case.
- Selection assessment: Feature-dependent.
- Scope limit: Targeted fix; stated validation limits apply.
- Integration note: When combined with VARIANT-HIDE-DISMISSED-500, retain both the decision merge and the null-safe row lookup.

Publication is performed by the user when selected:

```bash
git -C /home/jakob/src/codex/bonsai push -u origin pr/tb-no-amr-500
```
