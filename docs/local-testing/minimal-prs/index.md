# Local P0/P1 fix candidates

Actual minimal production patches are prepared in 39 local branches for 38 findings: 35 Bonsai branches and four SDK branches, including one paired upload companion. No branch or PR has been published. The development baseline catalog remains unchanged by candidate status.

**Privacy remains conditional:** the public-only creation candidate rejects new private-marked records. Existing private records are not protected; a private-data deployment still has an open P0.

Workflow exposure is inferred from the observed trigger and pinned source, not measured production frequency. Real JASEN input, local account practices and feature usage have not been supplied. Severity remains the development catalog's assessment. Exact patch sizes are measured against each candidate's stated base; prerequisite changes are additional.

Review severity, the chance of encountering the stated trigger in this installation, and the size of the required change together. A small patch is not by itself proof of low risk. 'Early review' suggests review order, not authorization to merge.

All 39 candidate heads passed their focused checks (91 checks). A detached composition passed API/frontend/SDK regressions, TypeScript checking and a production webpack build. This is bounded software verification, not live ingestion or diagnostic validation.

The reusable checks and PR bodies stay on the audit branch; each production branch contains only its scoped fix. Three branches are stacked on explicit prerequisites. Two overlapping code areas require small import/line unions when selected together; details are in the affected bodies.

| Finding | Local branch | Base | Production lines | Review assessment |
| --- | --- | --- | --- | --- |
| [ORDINARY-RECORD-DELETE](ordinary-record-delete.md) | `pr/ordinary-record-delete` (Bonsai) | `development` | +2/-2, 1 files | Early review |
| [ACCOUNT-ROLE-PERMISSIONS](account-role-permissions.md) | `pr/account-role-permissions` (Bonsai) | `development` | +9/-9, 3 files | Early review |
| [ANALYSIS-UPLOAD-ROLE-GATE](analysis-upload-role-gate.md) | `pr/analysis-upload-role-gate` (Bonsai) | `pr/account-role-permissions` | +1/-1, 1 files | Early review |
| [PRIVATE-RECORD-SCOPE](private-record-scope.md) | `pr/private-record-scope` (Bonsai) | `development` | +2/-2, 1 files | Policy decision before release |
| [GROUP-DELETE-MEMBERSHIP-LOSS](group-delete-membership-loss.md) | `pr/group-delete-membership-loss` (Bonsai) | `development` | +1/-0, 1 files | Early review |
| [GROUP-MEMBERSHIP-LOSS](group-membership-loss.md) | `pr/group-membership-loss` (Bonsai) | `development` | +7/-2, 1 files | Early review |
| [METADATA-ADD-500](metadata-add-500.md) | `pr/metadata-add-500` (Bonsai) | `development` | +6/-6, 1 files | Early review |
| [RECOVERY-METADATA-LOSS](recovery-metadata-loss.md) | `pr/recovery-metadata-loss` (Bonsai) | `pr/metadata-add-500` | +5/-6, 1 files | Concurrency-dependent |
| [RECOVERY-COMMENT-IDENTITIES](recovery-comment-identities.md) | `pr/recovery-comment-identities` (Bonsai) | `development` | +15/-25, 1 files | Concurrency-dependent |
| [RECOVERY-GROUP-OVERLAP](recovery-group-overlap.md) | `pr/recovery-group-overlap` (Bonsai) | `development` | +17/-7, 3 files | Concurrency-dependent |
| [METADATA-CATEGORY-LOSS](metadata-category-loss.md) | `pr/metadata-category-loss` (Bonsai) | `development` | +1/-1, 1 files | Early review |
| [METADATA-TABLE-EMPTY](metadata-table-empty.md) | `pr/metadata-table-empty` (Bonsai) | `development` | +21/-7, 3 files | Feature-dependent |
| [CSV-EMPTY-CELL-500](csv-empty-cell-500.md) | `pr/csv-empty-cell-500` (Bonsai) | `development` | +7/-1, 1 files | Early review |
| [CURATION-DOUBLE-SUBMIT](curation-double-submit.md) | `pr/curation-double-submit` (Bonsai) | `development` | +1/-5, 2 files | Early review |
| [SELECTED-FILTER-STALE](selected-filter-stale.md) | `pr/selected-filter-stale` (Bonsai) | `development` | +1/-0, 1 files | Early review |
| [VARIANT-SELECT-ALL-INVALID](variant-select-all-invalid.md) | `pr/variant-select-all-invalid` (Bonsai) | `development` | +2/-2, 1 files | Early review |
| [VARIANT-FILTER-AND](variant-filter-and.md) | `pr/variant-filter-and` (Bonsai) | `development` | +2/-2, 1 files | Early review |
| [VARIANT-HIDE-DISMISSED-500](variant-hide-dismissed-500.md) | `pr/variant-hide-dismissed-500` (Bonsai) | `development` | +2/-1, 1 files | Early review |
| [QC-FILTER-EMPTY](qc-filter-empty.md) | `pr/qc-filter-empty` (Bonsai) | `development` | +7/-1, 2 files | Early review |
| [GROUP-MEMBERSHIP-LIMIT](group-membership-limit.md) | `pr/group-membership-limit` (Bonsai) | `development` | +8/-7, 1 files | Feature-dependent |
| [ADMIN-CREATE-USER-500](admin-create-user-500.md) | `pr/admin-create-user-500` (Bonsai) | `development` | +3/-5, 1 files | Early review |
| [ADMIN-EDIT-USER-500](admin-edit-user-500.md) | `pr/admin-edit-user-500` (Bonsai) | `development` | +7/-8, 2 files | Feature-dependent |
| [ACCOUNT-STALE-PAGES](account-stale-pages.md) | `pr/account-stale-pages` (Bonsai) | `development` | +15/-0, 1 files | Environment-dependent |
| [BASKET-UNDEFINED-ASSAY](basket-undefined-assay.md) | `pr/basket-undefined-assay` (Bonsai) | `development` | +7/-2, 1 files | Early review |
| [PRIVATE-GROUP-INVITE-500](private-group-invite-500.md) | `pr/private-group-invite-500` (Bonsai) | `development` | +3/-3, 2 files | Feature-dependent |
| [TB-CURATION-500](tb-curation-500.md) | `pr/tb-curation-500` (Bonsai) | `development` | +3/-1, 1 files | Early review |
| [ECOLI-VARIANTS-EMPTY](ecoli-variants-empty.md) | `pr/ecoli-variants-empty` (Bonsai) | `development` | +2/-2, 1 files | Early review |
| [DISPLAY-EMM-TABLE](display-emm-table.md) | `pr/display-emm-table` (Bonsai) | `development` | +2/-2, 1 files | Early review |
| [DISPLAY-EXTENDED-CONTEXT](display-extended-context.md) | `pr/display-extended-context` (Bonsai) | `development` | +1/-1, 1 files | Early review |
| [EMM-LIMS-EXPORT-500](emm-lims-export-500.md) | `pr/emm-lims-export-500` (Bonsai) | `development` | +5/-2, 1 files | Feature-dependent |
| [KLEBORATE-UPLOAD-422](kleborate-upload-422.md) | `pr/kleborate-upload-422` (Bonsai) | `development` | +5/-0, 2 files | Feature-dependent |
| [PARSER-MYKROBE-SELECTION](parser-mykrobe-selection.md) | `pr/parser-mykrobe-selection` (SDK) | `master` | +2/-0, 1 files | Early review |
| [PARSER-BRACKEN-EMPTY](parser-bracken-empty.md) | `pr/parser-bracken-empty` (SDK) | `master` | +1/-1, 1 files | Early review |
| [PARSER-COVERAGE-STREAM](parser-coverage-stream.md) | `pr/parser-coverage-stream` (SDK) | `master` | +4/-10, 1 files | Early review |
| [KLEBORATE-CLIENT-COMPANION](kleborate-client-companion.md) | `pr/kleborate-client-companion` (SDK) | `master` | +3/-2, 2 files | Feature-dependent |
| [PENDING-SAMPLE-500](pending-sample-500.md) | `pr/pending-sample-500` (Bonsai) | `development` | +6/-2, 2 files | Early review |
| [TB-NO-AMR-500](tb-no-amr-500.md) | `pr/tb-no-amr-500` (Bonsai) | `development` | +14/-7, 4 files | Feature-dependent |
| [RECOVERY-COMMENT-RETRY](recovery-comment-retry.md) | `pr/recovery-comment-retry` (Bonsai) | `pr/recovery-comment-identities` | +48/-14, 5 files | Concurrency-dependent |
| [EMM-DISPLAY-MISSING](emm-display-missing.md) | `pr/emm-display-missing` (Bonsai) | `development` | +9/-4, 2 files | Feature-dependent |

## Inspect and publish selected candidates

Inspect the exact local diff with `git diff BASE...BRANCH` in the stated repository. Review a branch in a separate worktree if desired. Keep prerequisite PRs as their own bases; after a prerequisite is merged, rebase its child onto the updated development branch. The SDK baseline is `master` at the recorded SDK commit.

The user can run the following commands for selected branches. Nothing here has been pushed:

```bash
git -C /home/jakob/src/codex/bonsai push -u origin pr/ordinary-record-delete
git -C /home/jakob/src/codex/bonsai push -u origin pr/account-role-permissions
git -C /home/jakob/src/codex/bonsai push -u origin pr/analysis-upload-role-gate
git -C /home/jakob/src/codex/bonsai push -u origin pr/private-record-scope
git -C /home/jakob/src/codex/bonsai push -u origin pr/group-delete-membership-loss
git -C /home/jakob/src/codex/bonsai push -u origin pr/group-membership-loss
git -C /home/jakob/src/codex/bonsai push -u origin pr/metadata-add-500
git -C /home/jakob/src/codex/bonsai push -u origin pr/recovery-metadata-loss
git -C /home/jakob/src/codex/bonsai push -u origin pr/recovery-comment-identities
git -C /home/jakob/src/codex/bonsai push -u origin pr/recovery-group-overlap
git -C /home/jakob/src/codex/bonsai push -u origin pr/metadata-category-loss
git -C /home/jakob/src/codex/bonsai push -u origin pr/metadata-table-empty
git -C /home/jakob/src/codex/bonsai push -u origin pr/csv-empty-cell-500
git -C /home/jakob/src/codex/bonsai push -u origin pr/curation-double-submit
git -C /home/jakob/src/codex/bonsai push -u origin pr/selected-filter-stale
git -C /home/jakob/src/codex/bonsai push -u origin pr/variant-select-all-invalid
git -C /home/jakob/src/codex/bonsai push -u origin pr/variant-filter-and
git -C /home/jakob/src/codex/bonsai push -u origin pr/variant-hide-dismissed-500
git -C /home/jakob/src/codex/bonsai push -u origin pr/qc-filter-empty
git -C /home/jakob/src/codex/bonsai push -u origin pr/group-membership-limit
git -C /home/jakob/src/codex/bonsai push -u origin pr/admin-create-user-500
git -C /home/jakob/src/codex/bonsai push -u origin pr/admin-edit-user-500
git -C /home/jakob/src/codex/bonsai push -u origin pr/account-stale-pages
git -C /home/jakob/src/codex/bonsai push -u origin pr/basket-undefined-assay
git -C /home/jakob/src/codex/bonsai push -u origin pr/private-group-invite-500
git -C /home/jakob/src/codex/bonsai push -u origin pr/tb-curation-500
git -C /home/jakob/src/codex/bonsai push -u origin pr/ecoli-variants-empty
git -C /home/jakob/src/codex/bonsai push -u origin pr/display-emm-table
git -C /home/jakob/src/codex/bonsai push -u origin pr/display-extended-context
git -C /home/jakob/src/codex/bonsai push -u origin pr/emm-lims-export-500
git -C /home/jakob/src/codex/bonsai push -u origin pr/kleborate-upload-422
git -C /home/jakob/src/codex/bonsai/bonsai-sdk push -u origin pr/parser-mykrobe-selection
git -C /home/jakob/src/codex/bonsai/bonsai-sdk push -u origin pr/parser-bracken-empty
git -C /home/jakob/src/codex/bonsai/bonsai-sdk push -u origin pr/parser-coverage-stream
git -C /home/jakob/src/codex/bonsai/bonsai-sdk push -u origin pr/kleborate-client-companion
git -C /home/jakob/src/codex/bonsai push -u origin pr/pending-sample-500
git -C /home/jakob/src/codex/bonsai push -u origin pr/tb-no-amr-500
git -C /home/jakob/src/codex/bonsai push -u origin pr/recovery-comment-retry
git -C /home/jakob/src/codex/bonsai push -u origin pr/emm-display-missing
```

Use the corresponding Markdown body when opening each PR. No `gh pr create` or remote publishing command has been executed.

## Reproduce the checks

```bash
python3 scripts/verify_minimal_prs.py
/home/jakob/data/codex/bonsai/environments/release-test/bin/python scripts/check_minimal_pr_browser.py
python3 scripts/check_minimal_pr_integration.py --validate
```

The three browser-only entries in the first command are deliberately deferred to the second command. Integration worktrees and builds are on the data drive; the live source overlays and records are unchanged.
