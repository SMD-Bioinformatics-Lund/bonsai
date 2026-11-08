# Deduplicate identified comment retries and preserve failed drafts

A lost response can cause another append of the same comment. There is no request identity; an error before acceptance can also lose the draft. Carry one actor-scoped request key through form, SDK headers and conditional append; retain a failed draft.

### How to setup and perform the tests

1. Keep the reusable audit harness available on `fix/critical-ui-release-pass` in `/home/jakob/src/codex/bonsai`. The production branch intentionally contains only the reported fix. Docker images and generic test dependencies are already cached on this machine.
2. From that checkout, run:

```bash
python3 scripts/verify_minimal_prs.py --only RECOVERY-COMMENT-RETRY
```

The harness extracts the candidate Git tree, so switching the running application checkout is unnecessary. Candidate checked: `66a99c96e7fa3478d7ab7bee23a98e3723e08502`.

### Expected outcome

A repeated identified request must store one comment; retain a draft after a known failed submission.

Recorded result: 6 focused checks passed (api, frontend). Logs and source heads are pinned in the local verification ledger. Requires RECOVERY-COMMENT-IDENTITIES. This is the largest candidate and crosses five files; session-expiry draft recovery remains separate.

### Additional context

- Finding: `RECOVERY-COMMENT-RETRY`; apparent priority: P1.
- Repository: Bonsai; base: `pr/recovery-comment-identities` (`34cbe08fed81255fd3d8d3d45b9763aabe5af934`).
- +48/-14 production lines in 5 file(s), relative to pr/recovery-comment-identities.
- Git prerequisites: RECOVERY-COMMENT-IDENTITIES.
- Paired repository candidate: None.
- Normal trigger: A comment is saved but its response is lost, then the same submission is retried. Stable-network sequential use is less exposed.
- Selection assessment: Concurrency-dependent.
- Scope limit: Targeted fix; stated validation limits apply.

Publication is performed by the user when selected:

```bash
git -C /home/jakob/src/codex/bonsai push -u origin pr/recovery-comment-retry
```
