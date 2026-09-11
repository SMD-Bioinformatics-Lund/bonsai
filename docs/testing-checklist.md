# Bonsai migration functional checklist

Use this checklist to verify that the migrated Bonsai instance supports its core
user workflows. Perform the checks with non-production test data.

## Test setup

- [ ] Open the Bonsai frontend and confirm that the landing page loads without visible errors.
- [ ] Prepare credentials for an administrator, a normal user, and an uploader account.
- [ ] Prepare at least two related test samples with valid analysis results and MinHash and SKA data.
- [ ] Prepare at least one sample that fails QC.
- [ ] Prepare test samples with AMR variants, metadata, MLST, and cgMLST results where applicable.
- [ ] Record the expected sample IDs, group memberships, QC results, species, typing results, and clustering relationships before testing.

## Authentication and navigation

- [ ] Log in as an administrator with valid credentials.
- [ ] Log out and confirm that authenticated pages are no longer accessible.
- [ ] Attempt to log in with an invalid password and confirm that a useful error is shown.
- [ ] Log in as a normal user and confirm that the main navigation and groups page load.
- [ ] Leave a session idle until its token expires, then confirm that the application returns to a usable login or logged-out page.

## User administration

- [ ] As an administrator, open the user administration page.
- [ ] Create a temporary user and assign the intended role or roles.
- [ ] Log in as the temporary user and confirm that its permissions match the assigned roles.
- [ ] Edit the temporary user's details or roles and confirm that the changes take effect.
- [ ] Delete the temporary user and confirm that it can no longer log in.
- [ ] As a normal user, confirm that administrator-only pages and actions are unavailable.

## Groups

- [ ] Open the group list and confirm that existing groups are displayed with understandable names and identifiers.
- [ ] Open an existing public group and confirm that its sample count and sample table are correct.
- [ ] Create a new test group and confirm that it appears in the group list.
- [ ] Edit the test group's display name, description, and visibility, then reload the page and confirm that the changes persist.
- [ ] Add test samples to the group and confirm that they appear in its sample table.
- [ ] Remove a test sample from the group and confirm that the page remains usable and the count is updated.
- [ ] Configure the group's allowed columns and confirm that unavailable columns cannot be selected.
- [ ] Select, reorder, and save table columns, then reload the page and confirm that the selection and order persist.
- [ ] Create or update a column preset and confirm that applying it changes the table as expected.
- [ ] Mark the group as a favorite and confirm that the favorite state persists after reloading.
- [ ] If private groups are used, confirm that the owner and invited users can see the group.
- [ ] If private groups are used, confirm that an uninvited normal user cannot see the group or access it directly by URL.
- [ ] Delete the test group and confirm that it disappears without affecting its samples.

## Samples

- [ ] Open the sample list or a group sample table and confirm that expected samples are present.
- [ ] Search, sort, filter, and paginate the sample table and confirm that the displayed results are correct.
- [ ] Open a sample and confirm that its human-readable sample ID or name is displayed correctly.
- [ ] Confirm that the sample's groups, timestamps, species, typing results, QC results, and available analysis cards match the expected data.
- [ ] Open the sample metadata view and confirm that scalar and tabular metadata are rendered correctly.
- [ ] Add a comment to a sample and confirm that it appears after reloading.
- [ ] Hide or remove the test comment and confirm that the action succeeds.
- [ ] Add samples to the basket, navigate between pages, and confirm that the basket contents and counter remain correct.
- [ ] Remove individual samples from the basket and clear the basket.

## Quality control

- [ ] Open a sample with a parsed QUAST or other QC result and confirm that its metrics are displayed correctly.
- [ ] Set the sample's QC classification to passed and confirm that the status persists after reloading.
- [ ] Set a failing test sample to failed, select an action, add a comment, and confirm that all values persist.
- [ ] Confirm that the failed-QC indication and available follow-up actions are displayed correctly elsewhere in the UI.

## Resistance results and curation

- [ ] Open a sample with AMR results and confirm that resistance genes and variants are displayed.
- [ ] Sort and filter the variants table and confirm that the visible rows match the selected filters.
- [ ] Select one or more test variants and submit a curation decision.
- [ ] Reload the page and confirm that the decision, rejection reason, phenotype, and resistance level are shown correctly where applicable.
- [ ] Confirm that accepted, rejected, and unprocessed variants use the expected visual state.
- [ ] Download the sample's LIMS export and confirm that the file opens and contains the expected sample and resistance values.

## Comparison and clustering

- [ ] Select multiple compatible samples and start a MinHash clustering job.
- [ ] Wait for the MinHash job to finish and confirm that a valid tree is displayed.
- [ ] Start an SKA clustering job and confirm that a valid tree is displayed.
- [ ] Start an MLST clustering job and confirm that a valid tree is displayed.
- [ ] Start a cgMLST clustering job and confirm that a valid tree is displayed.
- [ ] Confirm that job progress and failures are reported clearly rather than leaving a permanent loading indicator.
- [ ] Interact with the resulting tree, including labels, sample selection, metadata, and available layout controls.
- [ ] Run the "find similar samples" action for a sample and confirm that plausible matches are returned.
- [ ] Open the comparison view for selected samples and confirm that the expected comparison data is shown.
- [ ] Open alignment or genome-browser links for a sample with the required resources and confirm that the expected region and files load.

## Sample and analysis uploads

- [ ] Upload a new test sample through the normal uploader or manifest workflow.
- [ ] Confirm that the upload reports success and that the new sample appears in Bonsai without manually editing the database.
- [ ] Confirm that the uploaded sample ID, display name, metadata, and initial group memberships are correct.
- [ ] Upload or ingest a species prediction and confirm that the parsed result is visible on the sample page.
- [ ] Upload or ingest a QUAST or other QC result and confirm that its parsed metrics are visible.
- [ ] Upload or ingest an MLST result and confirm that its sequence type is visible and usable for clustering.
- [ ] Upload or ingest a cgMLST result and confirm that it is usable for clustering.
- [ ] Upload or ingest AMR results and confirm that genes and variants are visible in the resistance views.
- [ ] Upload the sample's MinHash signature using the supported file-upload format.
- [ ] Wait for MinHash indexing to finish, then confirm that the sample works in similarity search and MinHash clustering.
- [ ] Associate the sample with its SKA index and confirm that it works in SKA clustering.
- [ ] Attempt an upload with an invalid or incomplete manifest and confirm that it fails with a useful message and does not create a misleading partial sample.
- [ ] Attempt an upload with malformed analysis or signature data and confirm that it fails with a useful message.
- [ ] Repeat an upload for an existing sample and confirm that duplicate handling matches the intended behavior.

## Final regression pass

- [ ] Reload the main pages with the browser cache disabled and confirm that scripts, styles, images, and interactive controls load correctly.
- [ ] Repeat the primary sample and group workflows in each supported browser.
- [ ] Confirm that no tested action produced an unexpected server-error page, empty response, or permanent loading indicator.
- [ ] Record each failed check with the user role, sample or group ID, exact action, observed result, expected result, and relevant screenshot or log timestamp.
