# Render basket names literally and absent assay as empty text

A harmless b-tag record name becomes HTML in the basket. A missing optional assay also appears as the literal undefined label. Escape the name at its HTML insertion and render absent assay as empty text.

### How to setup and perform the tests

1. Keep the reusable audit harness available on `fix/critical-ui-release-pass` in `/home/jakob/src/codex/bonsai`. The production branch intentionally contains only the reported fix. Docker images and generic test dependencies are already cached on this machine.
2. From that checkout, run:

```bash
python3 scripts/verify_minimal_prs.py --only BASKET-UNDEFINED-ASSAY
```

The harness extracts the candidate Git tree, so switching the running application checkout is unnecessary. Candidate checked: `a011b68355535d49b70ddbebaf38d8e572869fe0`.

### Expected outcome

Render names literally and give a readable empty value for the optional assay.

Recorded result: 1 focused checks passed (node). Logs and source heads are pinned in the local verification ledger. Literal presentation is tested. Script execution was not attempted or claimed.

### Additional context

- Finding: `BASKET-UNDEFINED-ASSAY`; apparent priority: P1.
- Repository: Bonsai; base: `development` (`21eccf7075fb59a897cb2ae86b0d6cdb95d0089c`).
- +7/-2 production lines in 1 file(s), relative to development.
- Git prerequisites: None.
- Paired repository candidate: None.
- Normal trigger: A record name contains HTML-like text, or its optional assay is absent. Simple alphanumeric names do not expose the markup interpretation.
- Selection assessment: Early review.
- Scope limit: Targeted fix; stated validation limits apply.

Publication is performed by the user when selected:

```bash
git -C /home/jakob/src/codex/bonsai push -u origin pr/basket-undefined-assay
```
