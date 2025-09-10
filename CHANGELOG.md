## [Unreleased]

### Added

- Added basic startup banner to the minhash service.
- Added support for storing sourmash index in RocksDB format.
- Added tags that warns the user if a sample might be contaminated. Thresholds are read from `thresholds.toml`file.
- Added button for showing only selected rows in the sample table
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

### Changed

- Added tooltip and helper text that describes how the find similar samples dropdown works.
- Add "add samples to group" button to the /groups/{group_id} view.
- Similarity searches from the groups view now only search among samples from the same group.
- Minhash service tasks are now executed through a dispatch function (`minhash_service/tasks/dispatch.py`)
- Display rejection reason and comments on mouse over in sample table
- Updated default columns in sample table
- TbProfiler and SV variants result  tables in the detailed variants view are now sortable and searchable.
- Added start position to detailed variants view
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
