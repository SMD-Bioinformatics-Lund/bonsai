## [Unreleased]

### Added

 - Improved output of create_user API CLI command
 - bonsai_api create-user command have options for mail, first name and last name.
 - Open samples by clicking on labels in the similar samples card in the samples view.

### Fixed

 - Fixed crash in create_user API CLI command
 - Resistance_report now render work in progress page
 - Removed old project name from GrapeTree header
 - Fixed issue that prevented node labels in GrapeTree from being displayed.

### Changed

 - The role "user" have permission to comment and classify QC

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