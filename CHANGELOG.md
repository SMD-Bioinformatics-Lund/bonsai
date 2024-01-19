## [Unreleased]

### Added

### Fixed

### Changed

## [v0.2.1]

### Added

 - Bulk QC status dropdown in group view

### Fixed

 - Fixed crash when clustering on samples without a MLST profile
 - Fixed bug that prevented adding samples to the basket in groups without "analysis profile" column
 - Fixed issue that prevented finding similar samples in group view
 - 500 error when trying to get a sample removed from the database
 - Frontend properly handles non-existing samples and group

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