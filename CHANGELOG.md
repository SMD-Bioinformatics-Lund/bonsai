## [Unreleased]

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
