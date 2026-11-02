# Bonsai manual UI testing checklist

Use the core pass for each deployment or release candidate. Reuse prepared test
samples and add focused extensions for the areas that changed. Before a major
release or migration, run the core and all applicable extensions. Use
non-production data; sample deletion uses disposable samples only.

## Choose the run

| Run | Scope |
| --- | --- |
| Core pass | The connected workflows below, including all four clustering methods and deletion. Aim initially for 20–30 minutes of active work with prepared data, plus job waiting time; adjust after timing a run. |
| Focused extensions | Add the relevant sections when authentication, groups, ingestion, analysis, clustering, deletion or browser support changes. |

Record the environment URL, deployed version, browser, date and selected
extensions once per run. Tick a box only when its expected result passes.
Annotate other results as **FAIL**, **BLOCKED** (for example, a missing fixture)
or **N/A** with a reason. Keep known defects as failures with an issue reference.
Missing required data is not a pass, and a successful API check does not establish
that its UI works. Record an expected wait limit for the small fixture jobs;
failed jobs or jobs exceeding that limit are failures, not blocked checks.

## Prepare reusable examples

Choose these examples once per test environment and keep a small expectations
table with their actual identifiers and values. Several roles can use the same
sample. Prepare administrator, normal-user and uploader credentials as needed.

| Role | Required data and recorded expectations |
| --- | --- |
| RELATED | Two or three samples of the same species and compatible typing schemes, with MLST/cgMLST alleles, MinHash signatures and SKA indexes. Record the exact sample set and expected relationships. Put them in a small test group so selecting all is practical. |
| DETAIL | Known species predictions, AMR genes/variants, curation states, scalar/tabular metadata and QC values. Include a TB example. Record variant count, genes, coordinates, displayed identifiers, read/depth values and a known nonzero duplicate-read count. |
| FAILED | A failed-QC sample with a recorded follow-up action and QC comment, plus a different general comment. |
| MISSING | A sample deliberately missing a signature or allele profile. Record which operation should fail and which input is absent. |
| DELETE | Two disposable samples in a test group and basket. Record their Sample IDs, names, internal IDs and memberships; keep an unselected sample as a control. For cleanup tests, give them working signatures first. Recreate these examples after a successful deletion. |

Use distinct Sample ID, Name and LIMS ID values in at least one example so a
wrong identifier is obvious. Record the expected reference, variant coordinate,
track names and gene-link destination for DETAIL. Include genes and applicable
grading/TBDB tracks in that expectation; unsupported features need a documented
product decision, not an assumed passing result.

The [synthetic local-test dataset](../e2e_tests/fixtures/local/README.md) provides
starting examples, expected results and preparation instructions; rerun,
missing-input and disposable cases may need additional setup. Its report metrics
are independent of its small BAM, so compare displayed QC to the source report.
Synthetic examples verify ingestion/display, not biological prediction accuracy.

## Core pass

### Find and inspect samples

- [ ] Open the landing page, log in as a normal user and open the groups/sample overview. Confirm the expected group names and counts appear without visible errors.
- [ ] Find DETAIL by its external Sample ID in the overview and a group table, using both text search and SearchBuilder. Confirm the result is the intended sample, not a match on Name or an internal UUID.
- [ ] Sort a known column, apply a filter and move between pages in a sufficiently populated table. Confirm the expected rows/order and clear the filter before continuing.
- [ ] Open DETAIL. Compare Sample ID, Name, LIMS ID, groups, timestamps, species and typing results with the expectations table. Confirm labels are consistent with the overview.
- [ ] Compare DETAIL's QC read count, depth and duplicate-read count with its source report. Check FAILED's status and hover its information icon: the QC action/comment must be distinguishable from the general Comments history. Allele QC must have a meaningful heading.
- [ ] Inspect the AMR overview and detailed variants table. Check the expected genes/variant count, coordinates, curation states and initial ordering; sort/filter once and verify the result. Check prediction headings and one gene-link destination against the recorded expectations. Species-summary wording should make clear whether it shows only the top hit.
- [ ] Open DETAIL's genome browser from a known variant. Confirm the expected reference and coordinate, readable alignment, and every recorded annotation track; a variant track alone is insufficient when other tracks are expected.

### Basket and comparison

- [ ] Add RELATED to the basket, navigate to another page and reload. Open the basket and confirm its exact contents agree with the badge count; a blank panel with a nonzero count fails.
- [ ] Log out and back in as the same user. Reopen the basket and confirm contents/count still agree and every card opens the correct sample.
- [ ] Run Find similar from the sample table and from a RELATED sample's detail page. Confirm the expected related samples appear without duplicates and the small tree uses the agreed readable identifiers.

Run each method on the recorded compatible set. For **every tree**, verify that
all selected samples are represented exactly once, including samples inside
collapsed nodes; expand them or inspect the metadata table. Labels and node links
must identify the correct samples, and relationships must match the fixture.
A partial tree or an error toast fails even if another method succeeds.

- [ ] MinHash: job completes and the tree meets the expectations above.
- [ ] SKA/SNV: job completes and the tree meets the expectations above.
- [ ] MLST: job completes using the known allele profiles and the tree meets the expectations above.
- [ ] cgMLST: job completes and the tree meets the expectations above.
- [ ] In one GrapeTree view, inspect metadata, change node labels/colour and select a sample. Confirm metadata matches the sample and No category appears only once. Open the sample comparison view and check the selected set and expected values.
- [ ] Attempt the recorded unsupported operation on MISSING. Confirm an understandable error identifies the sample by a readable identifier and explains the missing input. The page remains usable, loading finishes, and the message does not suggest an immediate retry will repair missing data.

### Delete disposable samples and finish

Log in as an administrator for this scenario. Record the DELETE examples and
unselected control before starting. Sample deletion removes samples from Bonsai;
removing a sample from a group is a separate action.

- [ ] Select and clear the selection; Delete samples must be unavailable with no selection. Select only DELETE and click Delete samples. Confirm that a prompt identifies the samples and count before any deletion. Cancel, reload and verify both samples still open and their group memberships and basket contents/count are unchanged.
- [ ] Repeat and confirm deletion. Wait for completion, then reload the overview, affected groups and basket: the selected samples are absent, counts agree, old sample links no longer open the records, and the unselected control still opens with unchanged memberships. Confirm the reported deleted count matches the actual outcome.

If clicking Delete immediately removes samples, record **FAIL** for confirmation
and stop this scenario to inspect the actual outcome. If the request fails or
times out, record the IDs and error, refresh and check which samples still exist;
do not infer the outcome from the toast or repeatedly retry an uncertain request.
Use the deletion-failure extension when investigating cleanup consistency.

- [ ] Remove one remaining test sample from the basket and check that only that card/count changes; then clear the basket and confirm an empty state and zero badge count.
- [ ] Log out and confirm authenticated pages are no longer accessible. Record failures, unexpected empty panels, errors or unfinished loading encountered during the pass.

## Focused extensions

### Authentication and user administration

Run for changes to login, sessions, roles or user administration.

- [ ] Try an invalid password and an expired session. Confirm useful login/session messages and a usable route back to login.
- [ ] As administrator, create a temporary user, log in with its assigned roles, then edit its details/roles and verify the changes after reloading or logging in again.
- [ ] Confirm a normal user cannot access administrator pages/actions directly. Delete the temporary user and confirm it can no longer log in.
- [ ] Switch between two users in the same browser. Confirm the basket follows the agreed per-user behaviour and its counter/cards never disagree or expose another user's saved selection.

### Groups and table configuration

Run for changes to groups, memberships, columns or table state.

- [ ] Create a group; edit its name, description and visibility, mark it as a favorite and reload. Confirm the group list and details retain the changes.
- [ ] Add and remove sample memberships. Confirm the group's rows/count and the sample's group list agree after reload; removing membership must leave the sample accessible elsewhere.
- [ ] Configure allowed columns, then select/reorder/save columns and apply a saved preset. Confirm persistence and that disallowed columns are unavailable. Check Sample ID remains searchable.
- [ ] For private groups, verify owner/invited access and reject an uninvited normal user, including direct URLs.
- [ ] Delete the test group and verify its samples remain accessible and no longer list the deleted membership.

### Metadata and analysis results

Run for changes to parsing, sample detail layout, QC, comments, AMR or exports.

- [ ] Check scalar and tabular metadata against the source. If clinical/test classification is supported, verify the agreed value in details, tables and filters; distinguish it from pipeline release stage.
- [ ] Add a general comment, reload, then hide/remove it. Confirm the visible history/count updates and the separate QC comment is unchanged.
- [ ] Change a disposable example to passed, then failed with an action/comment. Reload and check details/table/tooltip agreement; restore its original QC state afterward.
- [ ] Curate test variants to accepted/rejected and leave one unprocessed. Reload and verify decisions, rejection reason, phenotype, resistance level and visual state; compare initial sorting with the agreed order.
- [ ] Download the LIMS export and compare the sample and resistance values with the expected results, including which prediction tool supplied them.
- [ ] On one TB and one non-TB detail page, review headings, AMR/virulence/other prediction grouping and tooltips. Check gene/region identifiers and link labels against the agreed display contract; record unclear terminology as a UX finding.

### Uploads and data readiness

Run for changes to ingestion, parsers, identifiers, worker configuration or
resource paths. Use the normal uploader/manifest workflow and the uploader account.

- [ ] Upload a new sample and its species, QC, MLST/cgMLST and AMR reports. Confirm success without manual database edits and compare identifiers, metadata, initial memberships and displayed results with the inputs.
- [ ] Upload its MinHash signature and wait for both registration and indexing to finish. Find similar and cluster the fresh sample with RELATED; upload acceptance alone is insufficient.
- [ ] Associate its SKA index and verify SNV clustering includes the fresh sample. Open its registered browser resources and check tracks/coordinates.
- [ ] Submit an incomplete manifest and malformed analysis/signature data. Confirm useful errors and no misleading successful/ready state or replacement of previously valid results.
- [ ] Repeat an existing upload to check duplicate handling. After a deliberately failed signature upload in an isolated test environment, correct the input and verify recovery reaches a usable indexed state.

### Clustering edge cases

Run for changes to clustering, sample identity, signatures or data migration.

- [ ] Cluster an original and rerun together, including SKA inputs with shared upstream sequence labels. Confirm no Duplicate names error, no overwritten/omitted samples and correct links despite similar display names.
- [ ] Contrast a sample with no MLST alleles with one having an unknown ST but a valid compatible allele profile. Reject the missing profile with readable sample identifiers; the unknown ST alone must not prevent clustering.
- [ ] Add MISSING or a failed/excluded sample to an otherwise compatible selection. Confirm the agreed rejection/eligibility behaviour, clear affected-sample names, no silent partial tree and no stuck loading state. Check an unrelated or incompatible sample is handled according to the method's documented requirements.
- [ ] Leave an obsolete sample ID in the basket by deleting a disposable sample or using a prepared stale-selection case. Reload/reopen and verify the count/cards reconcile and an unavailable API produces a visible error rather than a blank panel.

### Deletion failure and cleanup

Run for changes to deletion, audit logging, transactions or worker cleanup. Inject
failures only in an isolated test environment with disposable samples.

- [ ] Cause a controlled deletion failure before commit and verify samples/memberships remain unchanged. For a timeout where the commit outcome is unknown, establish it from refreshed records and audit/request logs. Check basket and cleanup jobs agree with the result; the UI must not report an unverified success or hide a partial outcome.
- [ ] After success or rollback, verify signature metadata/index eligibility agrees with whether the sample still exists. A surviving sample must retain its working similarity/clustering data; a deleted sample must not return as a similarity hit after cleanup completes. Include a surviving sample sharing the signature checksum to catch over-deletion.

### Browser and deployment checks

Run for changes to frontend assets/browser support and before major releases.

- [ ] Reload the main views with the cache disabled. Confirm scripts, styles, images and controls load, and record the deployed versions if behaviour differs between environments.
- [ ] Repeat the main sample, basket and tree interactions in each supported browser. Focus on browser behaviour rather than repeating all data-entry scenarios.

## Supporting checks and failure notes

The [API smoke checks](../e2e_tests/fixtures/local/smoke_test.py) and
[expanded scenarios](../e2e_tests/fixtures/local/scenario_test.py) can help verify
the prepared synthetic dataset, clustering and parsed values. Follow their
[setup instructions](../e2e_tests/fixtures/local/README.md); they expect that
dataset and do not replace the browser checks above.

After deployment or migration, `bonsai-api doctor --output /tmp/doctor.tsv` in
the configured API container can help distinguish missing files, signature
metadata and index eligibility from UI failures. See the
[administration guide](source/administration.rst) for configuration and limits.

For each failed check, record only the information needed to reproduce it:
scenario, user role, Sample ID/name plus internal ID, exact action, expected and
actual result, and screenshot or error/request/job ID with a timestamp when
available. Missing fixtures block a check; distinguish them from an upload or
background job that failed while preparing a valid fixture. Record that failure
and its job/error details rather than dismissing it as a frontend problem.
