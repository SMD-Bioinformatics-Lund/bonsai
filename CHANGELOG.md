## [Unreleased]

### Added

- API can automatically create an admin user on first startup if `BONSAI_ADMIN_USER` and `BONSAI_ADMIN_PASSWORD` is set.
- Database indexes are now created automatically on API startup.
- Added a GET /memberships router for querying samples belonging to groups and vice versa.
- Show groups a sample is a member of in the sample table.
- Added button for showing only selected rows in the sample table
- Added an isolated local test environment with generated synthetic samples and MinHash and SKA artifacts. [#444](https://github.com/SMD-Bioinformatics-Lund/bonsai/pull/444)
- Added an `npm run watch` command for rebuilding frontend assets during development. [#446](https://github.com/SMD-Bioinformatics-Lund/bonsai/pull/446)
- Added a manual UI testing checklist for core Bonsai workflows. [#459](https://github.com/SMD-Bioinformatics-Lund/bonsai/pull/459)

### Fixed

- Handle structured MinHash similarity results and expand shared signatures to every eligible sample. This resolves an issue where "Find similar" crashed or selected only one sample per checksum. (PR #TBD)
- Sort MinHash matches by similarity before applying limits, with stable ordering for ties. (PR #TBD)
- Rebuild the MinHash index from eligible metadata to repair missing, stale, or duplicate entries and reconcile index flags; report metadata update failures. Repair omits excluded samples and replaces the old `--include-excluded` option. (PR #TBD)
- Make MinHash integrity checks account for shared-signature eligibility and use the correct deletion flag. (PR #TBD)
- Prevent duplicate MinHash index entries, correctly track samples sharing a checksum, and preserve shared signatures during deletion and QC exclusion. (PR #TBD)
- Fixed regression that prevented sampels from being removed
- Remove sample from group now uses the correct group id in the API call.
- Ska trying to find missing index files now properly walks results directory.
- Fixed MinHash signature upload serialization. [#444](https://github.com/SMD-Bioinformatics-Lund/bonsai/pull/444)
- Display a placeholder instead of crashing when sample metadata is missing from the clustering view. [#444](https://github.com/SMD-Bioinformatics-Lund/bonsai/pull/444)
- Fixed group selector preselection and saving allowed columns in the group editor. [#446](https://github.com/SMD-Bioinformatics-Lund/bonsai/pull/446)
- Fixed frontend group creation routing and post-creation state, preventing crashes and false failure messages. [#446](https://github.com/SMD-Bioinformatics-Lund/bonsai/pull/446)
- Show the underlying error when adding samples to a group fails. [#446](https://github.com/SMD-Bioinformatics-Lund/bonsai/pull/446)
- Reload the frontend asset manifest after a rebuild so updated asset filenames take effect. [#449](https://github.com/SMD-Bioinformatics-Lund/bonsai/pull/449)
- Let the API generate group UUIDs when groups are created through the CLI. [#451](https://github.com/SMD-Bioinformatics-Lund/bonsai/pull/451)
- Fixed group tables failing to load their configured columns after the API response format changed. [#452](https://github.com/SMD-Bioinformatics-Lund/bonsai/pull/452)
- Return a valid QC classification when an update does not change the sample status. [#456](https://github.com/SMD-Bioinformatics-Lund/bonsai/pull/456)
- Apply the correct analysis-index action after QC updates: include passed and unprocessed samples, and exclude failed samples. [#456](https://github.com/SMD-Bioinformatics-Lund/bonsai/pull/456)
- Immediately refresh QC status cells and tooltips after successful updates. [#456](https://github.com/SMD-Bioinformatics-Lund/bonsai/pull/456)
- Reject clustering requests when selected samples lack the requested typing profile or SKA index, and identify affected samples by Lab ID. [#457](https://github.com/SMD-Bioinformatics-Lund/bonsai/pull/457)
- Show clustering API validation details in frontend notifications and reliably clear loading indicators after failures. [#457](https://github.com/SMD-Bioinformatics-Lund/bonsai/pull/457)
- Preserve concise background-job errors and surface them in the sample dendrogram view. [#457](https://github.com/SMD-Bioinformatics-Lund/bonsai/pull/457)
- Use the current API client argument when posting sample comments. [#459](https://github.com/SMD-Bioinformatics-Lund/bonsai/pull/459)
- Surface queued clustering worker errors in basket notifications. [#458](https://github.com/SMD-Bioinformatics-Lund/bonsai/pull/458)
- Return valid status details when MinHash signatures are removed from RocksDB indexes. [#458](https://github.com/SMD-Bioinformatics-Lund/bonsai/pull/458)
- Load DataTables exports through the frontend bundle without requiring global jQuery. [#472](https://github.com/SMD-Bioinformatics-Lund/bonsai/pull/472)
- Refresh group-card sample counts after group memberships change. [#468](https://github.com/SMD-Bioinformatics-Lund/bonsai/pull/468)
- Limit Select all in sample tables to rows matching the active filters. [#473](https://github.com/SMD-Bioinformatics-Lund/bonsai/pull/473)
- Validate and persist initial group memberships using internal sample IDs when creating samples through the API. [#474](https://github.com/SMD-Bioinformatics-Lund/bonsai/pull/474)
- Roll back sample creation and membership counters when required audit logging fails. [#474](https://github.com/SMD-Bioinformatics-Lund/bonsai/pull/474)

### Changed

- Use Lab IDs as node labels in GrapeTree and sample dendrograms. [#457](https://github.com/SMD-Bioinformatics-Lund/bonsai/pull/457)
- Exclude internal sample UUIDs from user-facing clustering metadata while retaining them as tree join keys. [#457](https://github.com/SMD-Bioinformatics-Lund/bonsai/pull/457)
- Use Lab IDs in resistance and metadata page titles. [#457](https://github.com/SMD-Bioinformatics-Lund/bonsai/pull/457)
- Sample collection now keep track of group memberships.
- An user can now add samples to multiple groups at the same time.
- Improved seeding of a development Bonsai database with a new `seed_db.py` script.
- TbProfiler and SV variants result  tables in the detailed variants view are now sortable and searchable.
- Added start position to detailed variants view
- Improved frontend API error handling by parsing structured problem-details responses for delete, group removal, QC update, and similar-sample operations.
- Batch sample QC updates now wait for all selected samples, report partial failures, and prevent empty submissions. [#456](https://github.com/SMD-Bioinformatics-Lund/bonsai/pull/456)
- Improved API error handling if audit log service became unreachable after startup.
- Controlled logout page on logout / session expiry. [#454](https://github.com/SMD-Bioinformatics-Lund/bonsai/pull/454)
- Updated Python service base images to Debian Trixie (bullseye was getting deprecated). [#444](https://github.com/SMD-Bioinformatics-Lund/bonsai/pull/444)
- Updated the frontend TypeScript, ESLint, and build-tool dependencies. [#447](https://github.com/SMD-Bioinformatics-Lund/bonsai/pull/447)

## [v2.1.0]

### Added

- Improved LIMS export function that can be customised using a export configd

### Fixed

- Fixed issue in lineage card that could crash javascript
- Fixed regression in GrapeTree that prevented multiple node labels to be displayed.

## [v2.0.0]

### Added

- Split `BONSAI_API_URL` to two URLs, one for internal frontend-api communication and one for external browser to api communication.
- Added sequencing run id to sample page

### Fixed

- Options to make columns sortable, searchable, and visibility are now stored properly.
- Fixed workflow for publishing docker images on tagged releases.
- Fixed delete samples bug.
- Fixed `upload_sample.py` add to group bug.
- Fixed close basket bug.
- Fixed find closest samples bug.
- Fixed sort on date
- Fixed overlapping table
- Fixed missing QC column in QC view
- Fixed faulty display of analysis metadata in `Pipeline` and `Databases` cards
- Fixed routing path bugs
- Fixed find and cluster similar samples calling bug
- Fixed signature removal bug
- Fixed faulty adding of signature to index bug
- Fixed grapetree rendering with apache subdir
- Fixed ska clustering timeout bug by increasing retries to 100

### Changed

- Display rejection reason and comments on mouse over in sample table
- Updated default columns in sample table
- Entrypoint GET `/samples` was changed to POST `/samples/summary` to mitigate URL length limitations.
- Moved javascript from jinja templates into typescript modules and refactored some page elements into web components.
- Updated `WebDriverWait` time in e2e tests.
- Updated minhash error throwing for missing sig files

## [v1.2.0]

### Added

- Added support to add metadata to samples through the config file.
- Added sample `assay` and `release_life_cycle` to table and sample overview
- Added better logging for minhash calls
- Added task to JobStatus model

### Changed

- Uppdated prp to version 1.3.1

### Fixed

- Fixed number of missing alleles displayed from cgmlst

## [v1.1.0]

### Added

- Added the option to select what info is being displayed on mousehover in GrapeTree
- Added CLI command for validating paths to index and reference files.
- The CLI command `validate-paths` can send reports via mail.

### Changed

### Fixed

- Multiple node labels are now being displayed for grouped nodes in GrapeTree
- Greater than and lesser than are now being remembered when filtering varians in variants.
- A redis connection error no longer crash the sample view in the frontend.

## [v1.0.0]

### Added

- Added a test mode for the frontend that is set using an env variable.
- Added SNV clustering using SKA indexes.
- Added card for displaying EMM typing result from emmtyper.
- Added mlst scheme to mlst card.
- Added support for timezones in frontend.

### Changed

- Added dummy SKA indexes for test samples.
- Updated PRP to version 0.11.3
- Added underscores to AMRs in LIMS export.

### Fixed

- Empty groups of samples are now being displayed as being empty.
- Dates are now being handled properly in the sample tables.
- Fixed padding of sample table in group and groups view.
- Fixed issue preventing virulence predictions to be shown.
- Fixed display issues of ResFinder variants.
- Timestamps are now correctly assigned.
- `created_at` timestamp are not overwritten when updating a group.
- Fixed broken sample counter in the group view.

## [v0.8.0]

### Added

- Added select all variants button to tbprofiler and SV cards in Variant report view.
- Added button to the groups view for adding selected samples to group.
- Added button to the group view for removing selected samples from group.
- Added column with comments indicator to group and groups view.
- Added foundation for testing API routes.
- Added test for Allele cluster service.

### Changed

- Genome coverage plot to interactive and have an y-range of 0 to 100.
- Use data-tables instead of w2ui for samples tables.
- Improved error handling of allele cluster service.
- Removed swedish characters from LIMS export output.

### Fixed

- Fixed highlight of displayed sample in the dendrogram on the sample view page.
- Fixed formatting of grapetree metadata that could crash the frontend.
- Fixed crash in Allele cluster service when clustering samples with the same profile using MsTree or MsTreeV2.

## [v0.7.0]

### Added

- Can configure SSL verification and usage of SSL certs for API requests from frontend.
- Added cards ShigaPass result and function to tag Ecoli and Shigella spp with ShigaPass result.
- Added option to filter variants on WHO class and variant type in the variants view.
- Added button to reset variants filter on the variants view.
- Added support for more IGV annoation file formats.

### Changed

- Bonsai now uses sample ids created by Jasen to identify unique samples.
- Updated PRP to version 0.10.1
- Improved installation instructions.
- Updated requests to version 2.32.0
- Added startup commands to minhash and allele clustering services Dockerfiles.
- Use pydantic-settings for config management in frontend.
- Updated the samples tables to make sample name, sample id, and major spp searchable.
- Truncate long tbprofiler variant names and show full name on hover.
- Fixed issue that could prevent IGV from loading.
- Updated IGVjs to version 3.0.2
- Updaed how AMR variants are displayed on the sample view page. All varians are displayed if no variant have been processed, otherwise only show passed resistance yielding variants.

### Fixed

- Fixed misalignment of the checkbox in the samples table in the group and groups view.
- Fixed bug in the TB lineage card that could crash the frontend.
- Fixed an issue where samples without MLST profiles could crash GrapeTree.
- Fixed removal of new ChewBBACA alleles call info codes.

## [v0.6.0]

### Added

- Added source of tbprofier db entry as badge to result card.
- Added species and phylogroup prediction from Mykrobe.

### Changed

- Updated IGVjs to version 2.15.11
- Updated PRP to version 0.8.3
- Updated the formatting of the results table in the tbprofiler card.

### Fixed

- Fixed bug in generating mongodb URI
- Fixed crash if vcf type was not recognized
- Fixed bug that prevented samples to be reomved from the basket.
- Improved error handling if a sample could not be removed from the basket.

## [v0.5.0]

### Added
- Show the same metadata in grapetree as in the sample table from the groups and group view.
- Added optional LDAP based authentication system

### Changed
- Show disabled IGV button for samples without BAM or reference genome. 
- Updated LIMS export format

### Fixed

## [v0.4.1]

### Added

- Display LIMS id in samples view

### Changed

- Sample name is being displayed instead of sample id on the samples view
- Dockerfile chown step for api and frontend

### Fixed

- Fix minhash sample id lookup by storing sample_id as signautre name when signature is written to disk.
- Links to a sample from the samples tables now works when Bonsai is hosted under a sub-path
- Fixed so the samples could be added to the minhash index
- Fixed nameing of signature sketches and updating filename
- Fixed broken URL that prevented finding similar samples
- Fixed storing of selected samples in browser session that prevented samples to be added to the basket from the groups view.
- Fixed broken URLs in dendrogram in samples view
- Fixed crash when reading empty sourmash index
- Fixed crash in resistance/variants view when a samples did not have SNVs or SV variants

## [v0.4.0]

### Added

- Added Sample name, LIMS ID, and Sequencing run as selectable columns
- Sample name in sample view table links to sample
- New upload script (`upload_sample.py`) that takes a upload config in YAML format as input

### Fixed

### Changed

- Sample id is assigend by concating `lims_id` and `sequencing_run`
- Sample id is not displayed by default
- API route POST /samples/ returns `sample_id`
- Removed `upload_sample.sh`

## [v0.3.0]

### Added

 - Add button to remove samples from the group- and groups view.
 - Added view for analyszing variants with filtering
 - Added IGV genome browser integration to variant analysis view.
 - Bonsai support display of SV and SNV variants.
 - A user can classify variant as accepted or as rejected based and annotate why it was dissmissed.
 - A user can annotate that a variant yeilds resistance to additional anitbiotics
 - Placeholder Export to LIMBS button to the sidebar in the variants view
 - Added CLI command for exporting AMR prediction to a LIMS tsv file

### Fixed

 - 500 error when trying to get a sample removed from the database
 - Frontend properly handles non-existing samples and group
 - Fixed typo in similar samples card that caused invalid URLs
 - Fixed default fontend config to work with default docker-compose file

### Changed

 - Removed "passed qc" column from tbprofiler result
 - Changed default app port to 8000 and api port to 8001

## [v0.2.1]

### Added

 - Bulk QC status dropdown in group view

### Fixed

 - Fixed crash when clustering on samples without a MLST profile
 - Fixed bug that prevented adding samples to the basket in groups without "analysis profile" column
 - Fixed issue that prevented finding similar samples in group view

### Changed

 - Display the sum of kraken assigned reads and added reads in spp card by default.
 - Froze uvicorn to version 0.25.0
 - Updated fastapi to version 0.108.0

## [v0.2.0]

### Added

 - Improved output of create_user API CLI command
 - bonsai_api create-user command have options for mail, first name and last name.
 - Open samples by clicking on labels in the similar samples card in the samples view.
 - Optional "extended" HTTP argument to sample view to view extended prediction info

### Fixed

 - Fixed crash in create_user API CLI command
 - Resistance_report now render work in progress page
 - Removed old project name from GrapeTree header
 - Fixed issue that prevented node labels in GrapeTree from being displayed.

### Changed

 - The role "user" have permission to comment and classify QC
 - Updated PRP to version 0.3.0

## [v0.1.0]

### Added

 - Find similar samples by calculating MinHash distance
 - Added async similarity searches and clustering
 - User can choose clustering method from the sample basket
 - Added spp prediction result to sample view
 - Find similar samples default to 50
 - Added STX typing for _Escherichia coli_ samples
 - CLI command for updating tags for all samples

### Fixed

 - Fixed calculation of missing and novel cgmlst alleles
 - Fixed so sample metadata is displayed in GrapeTree

### Changed

 - Renamed client to frontent and server to api
 - Renamed cgvis to Bonsai
 - Complete rewrite of the project
 - Removed N novel cgmlst alleles from cgmlst qc card
 - Use data models from JASEN Pipleine Result Processing application
 - Use pre-defined table columns in edit groups view
