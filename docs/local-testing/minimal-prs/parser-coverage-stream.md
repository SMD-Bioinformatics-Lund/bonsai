# Read coverage streams once and preserve every supplied row

The baseline parser consumes its stream and reads it again. A two-row generic stream retains only the first row, while path input works. Read the source once before parsing the rows.

### How to setup and perform the tests

1. Keep the reusable audit harness available on `fix/critical-ui-release-pass` in `/home/jakob/src/codex/bonsai`. The production branch intentionally contains only the reported fix. Docker images and generic test dependencies are already cached on this machine.
2. From that checkout, run:

```bash
python3 scripts/verify_minimal_prs.py --only PARSER-COVERAGE-STREAM
```

The harness extracts the candidate Git tree, so switching the running application checkout is unnecessary. Candidate checked: `1cd7ad6ec984aafea2386fe9156123ae7f2cb04d`.

### Expected outcome

Read once and preserve both rows identically for path and stream input.

Recorded result: 1 focused checks passed (sdk). Logs and source heads are pinned in the local verification ledger. The SDK branch preserves both rows for path and stream input; no coverage computation is run.

### Additional context

- Finding: `PARSER-COVERAGE-STREAM`; apparent priority: P1.
- Repository: SDK; base: `master` (`5789a9c7530407683f1fee9ffa450512269e62bc`).
- +4/-10 production lines in 1 file(s), relative to master.
- Git prerequisites: None.
- Paired repository candidate: None.
- Normal trigger: A multi-row coverage report is supplied as a stream, as in the API's TextIOWrapper path. File-path inputs avoid the consumed-stream problem.
- Selection assessment: Early review.
- Scope limit: Targeted fix; stated validation limits apply.

Publication is performed by the user when selected:

```bash
git -C /home/jakob/src/codex/bonsai/bonsai-sdk push -u origin pr/parser-coverage-stream
```
