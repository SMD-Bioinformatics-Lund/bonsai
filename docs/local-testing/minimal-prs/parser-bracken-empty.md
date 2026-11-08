# Return an empty list for header-only Bracken reports

A valid empty table is marked parsed and returns a nested dictionary instead of the declared result list. Return the defined empty-list shape for a header-only report.

### How to setup and perform the tests

1. Keep the reusable audit harness available on `fix/critical-ui-release-pass` in `/home/jakob/src/codex/bonsai`. The production branch intentionally contains only the reported fix. Docker images and generic test dependencies are already cached on this machine.
2. From that checkout, run:

```bash
python3 scripts/verify_minimal_prs.py --only PARSER-BRACKEN-EMPTY
```

The harness extracts the candidate Git tree, so switching the running application checkout is unnecessary. Candidate checked: `019d5904bd59eb58a6399ac02ba49c4106b93490`.

### Expected outcome

Return an empty envelope and empty list; retain numeric zero as a parsed value.

Recorded result: 1 focused checks passed (sdk). Logs and source heads are pinned in the local verification ledger. One-line SDK fix; frozen literal input only.

### Additional context

- Finding: `PARSER-BRACKEN-EMPTY`; apparent priority: P1.
- Repository: SDK; base: `master` (`5789a9c7530407683f1fee9ffa450512269e62bc`).
- +1/-1 production lines in 1 file(s), relative to master.
- Git prerequisites: None.
- Paired repository candidate: None.
- Normal trigger: A valid Bracken report has a header and no result rows. A populated report avoids the wrong empty-result shape.
- Selection assessment: Early review.
- Scope limit: Targeted fix; stated validation limits apply.

Publication is performed by the user when selected:

```bash
git -C /home/jakob/src/codex/bonsai/bonsai-sdk push -u origin pr/parser-bracken-empty
```
