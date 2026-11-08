# Honor selected result categories in the Mykrobe parser

Species-only and lineage-only requests raise UnboundLocalError although the full frozen report parses. Each branch needs its own result-type context. Use the defined result selection variable for both requested-category checks.

### How to setup and perform the tests

1. Keep the reusable audit harness available on `fix/critical-ui-release-pass` in `/home/jakob/src/codex/bonsai`. The production branch intentionally contains only the reported fix. Docker images and generic test dependencies are already cached on this machine.
2. From that checkout, run:

```bash
python3 scripts/verify_minimal_prs.py --only PARSER-MYKROBE-SELECTION
```

The harness extracts the candidate Git tree, so switching the running application checkout is unnecessary. Candidate checked: `3183b86d7aec72309b62e656ac3c969abba2fe7f`.

### Expected outcome

Selected values must match full-parse values while unrequested envelopes remain skipped.

Recorded result: 2 focused checks passed (sdk). Logs and source heads are pinned in the local verification ledger. Very small patch, but lower expected exposure in the default API workflow.

### Additional context

- Finding: `PARSER-MYKROBE-SELECTION`; apparent priority: P1.
- Repository: SDK; base: `master` (`5789a9c7530407683f1fee9ffa450512269e62bc`).
- +2/-0 production lines in 1 file(s), relative to master.
- Git prerequisites: None.
- Paired repository candidate: None.
- Normal trigger: An SDK caller requests one result category. The ordinary API ingestion path requests all categories and avoids this particular crash.
- Selection assessment: Early review.
- Scope limit: Targeted fix; stated validation limits apply.

Publication is performed by the user when selected:

```bash
git -C /home/jakob/src/codex/bonsai/bonsai-sdk push -u origin pr/parser-mykrobe-selection
```
