# Render current EMM descriptors and empty availability states

The summary checks emmtype while current descriptors use emm. Stored results have no card, including explicit empty-result states. Use the current descriptor and render populated, empty and unavailable states, including zero.

### How to setup and perform the tests

1. Keep the reusable audit harness available on `fix/critical-ui-release-pass` in `/home/jakob/src/codex/bonsai`. The production branch intentionally contains only the reported fix. Docker images and generic test dependencies are already cached on this machine.
2. From that checkout, run:

```bash
python3 scripts/verify_minimal_prs.py --only EMM-DISPLAY-MISSING
```

The harness extracts the candidate Git tree, so switching the running application checkout is unnecessary. Candidate checked: `a883d776f67a72980235c7fbc857ab39c8a64eff`.

### Expected outcome

Display positive, empty and unavailable descriptors and preserve numeric zero values.

Recorded result: 3 focused checks passed (frontend). Logs and source heads are pinned in the local verification ledger. Local frequency depends on whether this stored report category is used.

### Additional context

- Finding: `EMM-DISPLAY-MISSING`; apparent priority: P1.
- Repository: Bonsai; base: `development` (`21eccf7075fb59a897cb2ae86b0d6cdb95d0089c`).
- +9/-4 production lines in 2 file(s), relative to development.
- Git prerequisites: None.
- Paired repository candidate: None.
- Normal trigger: The summary receives the SDK's current EMM analysis type. All such descriptors are skipped by the obsolete template condition.
- Selection assessment: Feature-dependent.
- Scope limit: Targeted fix; stated validation limits apply.

Publication is performed by the user when selected:

```bash
git -C /home/jakob/src/codex/bonsai push -u origin pr/emm-display-missing
```
