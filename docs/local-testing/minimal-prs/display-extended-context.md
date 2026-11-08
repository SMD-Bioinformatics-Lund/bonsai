# Import extended-summary cards with record context

The imported card macro needs sample context when building a stored-row display link. Extended rendering returns HTTP 500 for the relevant record shape. Import the card macros with the existing request context.

### How to setup and perform the tests

1. Keep the reusable audit harness available on `fix/critical-ui-release-pass` in `/home/jakob/src/codex/bonsai`. The production branch intentionally contains only the reported fix. Docker images and generic test dependencies are already cached on this machine.
2. From that checkout, run:

```bash
python3 scripts/verify_minimal_prs.py --only DISPLAY-EXTENDED-CONTEXT
```

The harness extracts the candidate Git tree, so switching the running application checkout is unnecessary. Candidate checked: `45d812d891084c38064a2348f5d495c3d4d0efe3`.

### Expected outcome

Open the display-only extended summary and retain its supplied rows and links without executing an analysis or viewer action.

Recorded result: 1 focused checks passed (frontend). Logs and source heads are pinned in the local verification ledger. One template import changes; no linked viewer action is executed.

### Additional context

- Finding: `DISPLAY-EXTENDED-CONTEXT`; apparent priority: P1.
- Repository: Bonsai; base: `development` (`21eccf7075fb59a897cb2ae86b0d6cdb95d0089c`).
- +1/-1 production lines in 1 file(s), relative to development.
- Git prerequisites: None.
- Paired repository candidate: None.
- Normal trigger: The extended summary renders a supplied row with record-dependent links. Rows without those links may avoid the missing template context.
- Selection assessment: Early review.
- Scope limit: Targeted fix; stated validation limits apply.

Publication is performed by the user when selected:

```bash
git -C /home/jakob/src/codex/bonsai push -u origin pr/display-extended-context
```
