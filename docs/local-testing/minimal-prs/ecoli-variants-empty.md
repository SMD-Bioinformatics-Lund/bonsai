# Label the stored detail view with its supported result scope

The detail route selects only TBProfiler results yet reports No predicted resistance determinants for a record with stored AMRFinder results. State the supported stored-result type and point to the extended report.

### How to setup and perform the tests

1. Keep the reusable audit harness available on `fix/critical-ui-release-pass` in `/home/jakob/src/codex/bonsai`. The production branch intentionally contains only the reported fix. Docker images and generic test dependencies are already cached on this machine.
2. From that checkout, run:

```bash
python3 scripts/verify_minimal_prs.py --only ECOLI-VARIANTS-EMPTY
```

The harness extracts the candidate Git tree, so switching the running application checkout is unnecessary. Candidate checked: `4bd99d441ff66b7e1d013d5af6bbd3d0394b1edc`.

### Expected outcome

Distinguish unavailable or unsupported results from a negative result; define supported detail types.

Recorded result: 1 focused checks passed (frontend). Logs and source heads are pinned in the local verification ledger. This corrects the claim; it does not implement display support for additional result types.

### Additional context

- Finding: `ECOLI-VARIANTS-EMPTY`; apparent priority: P1.
- Repository: Bonsai; base: `development` (`21eccf7075fb59a897cb2ae86b0d6cdb95d0089c`).
- +2/-2 production lines in 1 file(s), relative to development.
- Git prerequisites: None.
- Paired repository candidate: None.
- Normal trigger: The stored detail page is opened for a result type the view does not render. The baseline message misleadingly resembles a negative finding.
- Selection assessment: Early review.
- Scope limit: Targeted fix; stated validation limits apply.

Publication is performed by the user when selected:

```bash
git -C /home/jakob/src/codex/bonsai push -u origin pr/ecoli-variants-empty
```
