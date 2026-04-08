# CHANGELOG

<!-- version list -->

## v1.3.0 (2026-04-08)

### Bug Fixes

- **entry**: Correctly initialize ctdam config file
  ([#23](https://github.com/DAM-CTD-Software/ctdam/pull/23),
  [`f231186`](https://github.com/DAM-CTD-Software/ctdam/commit/f231186acdd838e29f7856d0cea5f0c0bb0de047))

- **entry**: Fixed file path to via_config.toml
  ([#23](https://github.com/DAM-CTD-Software/ctdam/pull/23),
  [`f231186`](https://github.com/DAM-CTD-Software/ctdam/commit/f231186acdd838e29f7856d0cea5f0c0bb0de047))

- **parser**: Correct suffix check to distinguish file type
  ([#23](https://github.com/DAM-CTD-Software/ctdam/pull/23),
  [`f231186`](https://github.com/DAM-CTD-Software/ctdam/commit/f231186acdd838e29f7856d0cea5f0c0bb0de047))

### Chores

- Fix readme specification ([#22](https://github.com/DAM-CTD-Software/ctdam/pull/22),
  [`9b91dcb`](https://github.com/DAM-CTD-Software/ctdam/commit/9b91dcb2dd0a1b70f438afeda61930935ce98e9c))

- Ignore untracked git files inside sbs_data
  ([#23](https://github.com/DAM-CTD-Software/ctdam/pull/23),
  [`f231186`](https://github.com/DAM-CTD-Software/ctdam/commit/f231186acdd838e29f7856d0cea5f0c0bb0de047))

- **deps**: Added myst-parser and click-extra for markdown readme parsing in docs
  ([#21](https://github.com/DAM-CTD-Software/ctdam/pull/21),
  [`0a6b59d`](https://github.com/DAM-CTD-Software/ctdam/commit/0a6b59d1ea2b0fc243dd6a2bf569d733e813eb2b))

### Continuous Integration

- Run tests in one thread to avoid weird test artifacts from parallel testing
  ([#23](https://github.com/DAM-CTD-Software/ctdam/pull/23),
  [`f231186`](https://github.com/DAM-CTD-Software/ctdam/commit/f231186acdd838e29f7856d0cea5f0c0bb0de047))

### Documentation

- Added zenodo DOI badge to README ([#20](https://github.com/DAM-CTD-Software/ctdam/pull/20),
  [`ebe015e`](https://github.com/DAM-CTD-Software/ctdam/commit/ebe015e72278048c0d08ce8fd084eb25dac6bfb7))

- Correct github link resolving ([#21](https://github.com/DAM-CTD-Software/ctdam/pull/21),
  [`0a6b59d`](https://github.com/DAM-CTD-Software/ctdam/commit/0a6b59d1ea2b0fc243dd6a2bf569d733e813eb2b))

- Removed coverage badge which is not working
  ([#20](https://github.com/DAM-CTD-Software/ctdam/pull/20),
  [`ebe015e`](https://github.com/DAM-CTD-Software/ctdam/commit/ebe015e72278048c0d08ce8fd084eb25dac6bfb7))

- Replaced readme and index with markdown variant
  ([#21](https://github.com/DAM-CTD-Software/ctdam/pull/21),
  [`0a6b59d`](https://github.com/DAM-CTD-Software/ctdam/commit/0a6b59d1ea2b0fc243dd6a2bf569d733e813eb2b))

- Updated short description text ([#20](https://github.com/DAM-CTD-Software/ctdam/pull/20),
  [`ebe015e`](https://github.com/DAM-CTD-Software/ctdam/commit/ebe015e72278048c0d08ce8fd084eb25dac6bfb7))

### Features

- **entry**: Added a cli command that displays processing function descriptions
  ([#23](https://github.com/DAM-CTD-Software/ctdam/pull/23),
  [`f231186`](https://github.com/DAM-CTD-Software/ctdam/commit/f231186acdd838e29f7856d0cea5f0c0bb0de047))

- **entry**: Added a config file to ctdam, that can save external modules
  ([#23](https://github.com/DAM-CTD-Software/ctdam/pull/23),
  [`f231186`](https://github.com/DAM-CTD-Software/ctdam/commit/f231186acdd838e29f7856d0cea5f0c0bb0de047))

- **entry**: New cli command section that interacts with external functions
  ([#23](https://github.com/DAM-CTD-Software/ctdam/pull/23),
  [`f231186`](https://github.com/DAM-CTD-Software/ctdam/commit/f231186acdd838e29f7856d0cea5f0c0bb0de047))

- **proc**: Added a method that returns an external functions docstring
  ([#23](https://github.com/DAM-CTD-Software/ctdam/pull/23),
  [`f231186`](https://github.com/DAM-CTD-Software/ctdam/commit/f231186acdd838e29f7856d0cea5f0c0bb0de047))

- **proc**: Allow removal of external modules
  ([#23](https://github.com/DAM-CTD-Software/ctdam/pull/23),
  [`f231186`](https://github.com/DAM-CTD-Software/ctdam/commit/f231186acdd838e29f7856d0cea5f0c0bb0de047))

- **proc**: Module addition method to add external functions
  ([#23](https://github.com/DAM-CTD-Software/ctdam/pull/23),
  [`f231186`](https://github.com/DAM-CTD-Software/ctdam/commit/f231186acdd838e29f7856d0cea5f0c0bb0de047))

- **proc**: Neat output of newly added functions
  ([#23](https://github.com/DAM-CTD-Software/ctdam/pull/23),
  [`f231186`](https://github.com/DAM-CTD-Software/ctdam/commit/f231186acdd838e29f7856d0cea5f0c0bb0de047))

- **proc**: Use an external functions description as 'info' attribute
  ([#23](https://github.com/DAM-CTD-Software/ctdam/pull/23),
  [`f231186`](https://github.com/DAM-CTD-Software/ctdam/commit/f231186acdd838e29f7856d0cea5f0c0bb0de047))

### Testing

- **conv**: Handled syntax different between python 3.14.2 and 3.14.3
  ([#23](https://github.com/DAM-CTD-Software/ctdam/pull/23),
  [`f231186`](https://github.com/DAM-CTD-Software/ctdam/commit/f231186acdd838e29f7856d0cea5f0c0bb0de047))

- **proc**: Test external module removal ([#23](https://github.com/DAM-CTD-Software/ctdam/pull/23),
  [`f231186`](https://github.com/DAM-CTD-Software/ctdam/commit/f231186acdd838e29f7856d0cea5f0c0bb0de047))

- **proc**: Testing new module addition method
  ([#23](https://github.com/DAM-CTD-Software/ctdam/pull/23),
  [`f231186`](https://github.com/DAM-CTD-Software/ctdam/commit/f231186acdd838e29f7856d0cea5f0c0bb0de047))


## v1.2.0 (2026-03-26)

### Chores

- Reduce possible metadata errors for zenodo publishing
  ([#18](https://github.com/DAM-CTD-Software/ctdam/pull/18),
  [`72d7b9e`](https://github.com/DAM-CTD-Software/ctdam/commit/72d7b9e05ce4bc54bd557c9c60f03319554188a6))

- Update pyproject.toml to include netcdf dependencies
  ([#19](https://github.com/DAM-CTD-Software/ctdam/pull/19),
  [`cf3252b`](https://github.com/DAM-CTD-Software/ctdam/commit/cf3252bb0f7fd092da0e7b57bfe2d1422237b2e2))

### Continuous Integration

- **docs**: Fix plot html path ([#17](https://github.com/DAM-CTD-Software/ctdam/pull/17),
  [`074f165`](https://github.com/DAM-CTD-Software/ctdam/commit/074f165050877888c1f3b19e5722d3d42af750f5))

- **docs**: Run gh-pages when 'docs' was used in commit message
  ([#17](https://github.com/DAM-CTD-Software/ctdam/pull/17),
  [`074f165`](https://github.com/DAM-CTD-Software/ctdam/commit/074f165050877888c1f3b19e5722d3d42af750f5))

### Documentation

- Removed commented settings ([#17](https://github.com/DAM-CTD-Software/ctdam/pull/17),
  [`074f165`](https://github.com/DAM-CTD-Software/ctdam/commit/074f165050877888c1f3b19e5722d3d42af750f5))

- Replaced iframe in README with link to external plot page
  ([#17](https://github.com/DAM-CTD-Software/ctdam/pull/17),
  [`074f165`](https://github.com/DAM-CTD-Software/ctdam/commit/074f165050877888c1f3b19e5722d3d42af750f5))

### Features

- Add function to convert NMA Coordinates to decimal
  ([#19](https://github.com/DAM-CTD-Software/ctdam/pull/19),
  [`cf3252b`](https://github.com/DAM-CTD-Software/ctdam/commit/cf3252bb0f7fd092da0e7b57bfe2d1422237b2e2))

- Function to convert ctd data to netcdf format
  ([#19](https://github.com/DAM-CTD-Software/ctdam/pull/19),
  [`cf3252b`](https://github.com/DAM-CTD-Software/ctdam/commit/cf3252bb0f7fd092da0e7b57bfe2d1422237b2e2))

### Testing

- **parser**: Tests for to_netCDF function
  ([#19](https://github.com/DAM-CTD-Software/ctdam/pull/19),
  [`cf3252b`](https://github.com/DAM-CTD-Software/ctdam/commit/cf3252bb0f7fd092da0e7b57bfe2d1422237b2e2))


## v1.1.3 (2026-03-25)

### Bug Fixes

- **parser**: Propagate show_plot parameter also to create_main_html
  ([#16](https://github.com/DAM-CTD-Software/ctdam/pull/16),
  [`eac535a`](https://github.com/DAM-CTD-Software/ctdam/commit/eac535aff92e4b709c4e953a9ed982e9d4d2f6c4))

- **proc**: Adjust binning to allow bins below 1
  ([#16](https://github.com/DAM-CTD-Software/ctdam/pull/16),
  [`eac535a`](https://github.com/DAM-CTD-Software/ctdam/commit/eac535aff92e4b709c4e953a9ed982e9d4d2f6c4))

- **proc**: Cast bin_size to float to assure dot for splitting
  ([#16](https://github.com/DAM-CTD-Software/ctdam/pull/16),
  [`eac535a`](https://github.com/DAM-CTD-Software/ctdam/commit/eac535aff92e4b709c4e953a9ed982e9d4d2f6c4))

### Chores

- Added coverage dependency and configuration
  ([#14](https://github.com/DAM-CTD-Software/ctdam/pull/14),
  [`1d2dc87`](https://github.com/DAM-CTD-Software/ctdam/commit/1d2dc8747fd74f26dd4170b03434dd33a2d21aa6))

- Added coverage option that is missing for coverage-action
  ([#14](https://github.com/DAM-CTD-Software/ctdam/pull/14),
  [`1d2dc87`](https://github.com/DAM-CTD-Software/ctdam/commit/1d2dc8747fd74f26dd4170b03434dd33a2d21aa6))

### Continuous Integration

- Added python-coverage-comment-action for automatic coverage publishing
  ([#14](https://github.com/DAM-CTD-Software/ctdam/pull/14),
  [`1d2dc87`](https://github.com/DAM-CTD-Software/ctdam/commit/1d2dc8747fd74f26dd4170b03434dd33a2d21aa6))

- Split python-coverage-comment-action into two separate workflows
  ([#14](https://github.com/DAM-CTD-Software/ctdam/pull/14),
  [`1d2dc87`](https://github.com/DAM-CTD-Software/ctdam/commit/1d2dc8747fd74f26dd4170b03434dd33a2d21aa6))

- **docs**: Handled .html plot display in README and documentation
  ([#15](https://github.com/DAM-CTD-Software/ctdam/pull/15),
  [`d3f9cc7`](https://github.com/DAM-CTD-Software/ctdam/commit/d3f9cc79ef6c1205b2d4d1cda3c833f2dd4731b2))

### Documentation

- Added coverage badge ([#14](https://github.com/DAM-CTD-Software/ctdam/pull/14),
  [`1d2dc87`](https://github.com/DAM-CTD-Software/ctdam/commit/1d2dc8747fd74f26dd4170b03434dd33a2d21aa6))

- Fixed repo url and copyright year ([#15](https://github.com/DAM-CTD-Software/ctdam/pull/15),
  [`d3f9cc7`](https://github.com/DAM-CTD-Software/ctdam/commit/d3f9cc79ef6c1205b2d4d1cda3c833f2dd4731b2))

- Remove community info from zenodo settings
  ([#16](https://github.com/DAM-CTD-Software/ctdam/pull/16),
  [`eac535a`](https://github.com/DAM-CTD-Software/ctdam/commit/eac535aff92e4b709c4e953a9ed982e9d4d2f6c4))

- Updated docstrings ([#15](https://github.com/DAM-CTD-Software/ctdam/pull/15),
  [`d3f9cc7`](https://github.com/DAM-CTD-Software/ctdam/commit/d3f9cc79ef6c1205b2d4d1cda3c833f2dd4731b2))

- Updated README with more in-depth usage guides
  ([#15](https://github.com/DAM-CTD-Software/ctdam/pull/15),
  [`d3f9cc7`](https://github.com/DAM-CTD-Software/ctdam/commit/d3f9cc79ef6c1205b2d4d1cda3c833f2dd4731b2))

- Updated usage page with correct ctdam output and detailed Procedure usage
  ([#15](https://github.com/DAM-CTD-Software/ctdam/pull/15),
  [`d3f9cc7`](https://github.com/DAM-CTD-Software/ctdam/commit/d3f9cc79ef6c1205b2d4d1cda3c833f2dd4731b2))

- **vis**: Added example .html plot ([#15](https://github.com/DAM-CTD-Software/ctdam/pull/15),
  [`d3f9cc7`](https://github.com/DAM-CTD-Software/ctdam/commit/d3f9cc79ef6c1205b2d4d1cda3c833f2dd4731b2))

### Refactoring

- **parser**: Replaced CnvFile-specific export with general one from CTDData
  ([#14](https://github.com/DAM-CTD-Software/ctdam/pull/14),
  [`1d2dc87`](https://github.com/DAM-CTD-Software/ctdam/commit/1d2dc8747fd74f26dd4170b03434dd33a2d21aa6))

### Testing

- **parser**: Added test for output parser of GEOMAR ctd processing software
  ([#14](https://github.com/DAM-CTD-Software/ctdam/pull/14),
  [`1d2dc87`](https://github.com/DAM-CTD-Software/ctdam/commit/1d2dc8747fd74f26dd4170b03434dd33a2d21aa6))

- **parser**: Replaced dysfunctional test with new cnv export test
  ([#14](https://github.com/DAM-CTD-Software/ctdam/pull/14),
  [`1d2dc87`](https://github.com/DAM-CTD-Software/ctdam/commit/1d2dc8747fd74f26dd4170b03434dd33a2d21aa6))

- **proc**: Lower percentage of fitting bin sizes in binavg test
  ([#16](https://github.com/DAM-CTD-Software/ctdam/pull/16),
  [`eac535a`](https://github.com/DAM-CTD-Software/ctdam/commit/eac535aff92e4b709c4e953a9ed982e9d4d2f6c4))

- **proc**: Test binning in 0.1 dbar bins ([#16](https://github.com/DAM-CTD-Software/ctdam/pull/16),
  [`eac535a`](https://github.com/DAM-CTD-Software/ctdam/commit/eac535aff92e4b709c4e953a9ed982e9d4d2f6c4))


## v1.1.2 (2026-03-18)

### Bug Fixes

- **entry**: Avoid circular import in procedure_config_view
  ([#13](https://github.com/DAM-CTD-Software/ctdam/pull/13),
  [`90210bd`](https://github.com/DAM-CTD-Software/ctdam/commit/90210bddd755ad913d9764d5daad68f6471e02b6))


## v1.1.1 (2026-03-18)

### Bug Fixes

- Removed leading zeroes from station strings
  ([#12](https://github.com/DAM-CTD-Software/ctdam/pull/12),
  [`854c58b`](https://github.com/DAM-CTD-Software/ctdam/commit/854c58ba871bbac8fdb514d4ed85a4177712a61a))

- **proc**: Catch runtime warning in binavg, that pops up constantly
  ([#12](https://github.com/DAM-CTD-Software/ctdam/pull/12),
  [`854c58b`](https://github.com/DAM-CTD-Software/ctdam/commit/854c58ba871bbac8fdb514d4ed85a4177712a61a))

- **proc**: Correctly differentiate single or multiple return values
  ([#12](https://github.com/DAM-CTD-Software/ctdam/pull/12),
  [`854c58b`](https://github.com/DAM-CTD-Software/ctdam/commit/854c58ba871bbac8fdb514d4ed85a4177712a61a))

- **proc**: Handle file_suffix option differently than the other arguments
  ([#12](https://github.com/DAM-CTD-Software/ctdam/pull/12),
  [`854c58b`](https://github.com/DAM-CTD-Software/ctdam/commit/854c58ba871bbac8fdb514d4ed85a4177712a61a))

- **proc**: Output full external function name
  ([#12](https://github.com/DAM-CTD-Software/ctdam/pull/12),
  [`854c58b`](https://github.com/DAM-CTD-Software/ctdam/commit/854c58ba871bbac8fdb514d4ed85a4177712a61a))

- **proc**: Removed obsolete array update, that crashed most modules
  ([#12](https://github.com/DAM-CTD-Software/ctdam/pull/12),
  [`854c58b`](https://github.com/DAM-CTD-Software/ctdam/commit/854c58ba871bbac8fdb514d4ed85a4177712a61a))

- **proc**: Using numpydoc package for numpydoc docstring parsing
  ([#12](https://github.com/DAM-CTD-Software/ctdam/pull/12),
  [`854c58b`](https://github.com/DAM-CTD-Software/ctdam/commit/854c58ba871bbac8fdb514d4ed85a4177712a61a))

### Chores

- **deps**: Added numpydoc as dependency ([#12](https://github.com/DAM-CTD-Software/ctdam/pull/12),
  [`854c58b`](https://github.com/DAM-CTD-Software/ctdam/commit/854c58ba871bbac8fdb514d4ed85a4177712a61a))

- **docs**: Fixed link to github-pages documentation
  ([#12](https://github.com/DAM-CTD-Software/ctdam/pull/12),
  [`854c58b`](https://github.com/DAM-CTD-Software/ctdam/commit/854c58ba871bbac8fdb514d4ed85a4177712a61a))

### Continuous Integration

- Only run linting and testing when code chances detected
  ([#12](https://github.com/DAM-CTD-Software/ctdam/pull/12),
  [`854c58b`](https://github.com/DAM-CTD-Software/ctdam/commit/854c58ba871bbac8fdb514d4ed85a4177712a61a))

### Refactoring

- **proc**: Do not inherit from DataFile as long as not used
  ([#12](https://github.com/DAM-CTD-Software/ctdam/pull/12),
  [`854c58b`](https://github.com/DAM-CTD-Software/ctdam/commit/854c58ba871bbac8fdb514d4ed85a4177712a61a))

- **proc**: Removed obsolete check with file_suffix being its own attribute
  ([#12](https://github.com/DAM-CTD-Software/ctdam/pull/12),
  [`854c58b`](https://github.com/DAM-CTD-Software/ctdam/commit/854c58ba871bbac8fdb514d4ed85a4177712a61a))

- **proc**: Renamed exception for clarity ([#12](https://github.com/DAM-CTD-Software/ctdam/pull/12),
  [`854c58b`](https://github.com/DAM-CTD-Software/ctdam/commit/854c58ba871bbac8fdb514d4ed85a4177712a61a))

### Testing

- **proc**: Add testing of correct file_suffix behaviour
  ([#12](https://github.com/DAM-CTD-Software/ctdam/pull/12),
  [`854c58b`](https://github.com/DAM-CTD-Software/ctdam/commit/854c58ba871bbac8fdb514d4ed85a4177712a61a))

- **proc**: Update tests to use full external function names
  ([#12](https://github.com/DAM-CTD-Software/ctdam/pull/12),
  [`854c58b`](https://github.com/DAM-CTD-Software/ctdam/commit/854c58ba871bbac8fdb514d4ed85a4177712a61a))


## v1.1.0 (2026-03-16)

### Chores

- Fixed changelog format to allow auto-updating via PSR
  ([#7](https://github.com/DAM-CTD-Software/ctdam/pull/7),
  [`63bbd73`](https://github.com/DAM-CTD-Software/ctdam/commit/63bbd73597225896a39b2d5c32b25a313fe92eda))

- **deps**: Added tqdm for progress bar display in Casts
  ([#11](https://github.com/DAM-CTD-Software/ctdam/pull/11),
  [`a264130`](https://github.com/DAM-CTD-Software/ctdam/commit/a26413084e76bb56516b9a02af22c175110770fe))

### Continuous Integration

- Removed test code ([#8](https://github.com/DAM-CTD-Software/ctdam/pull/8),
  [`0f0f438`](https://github.com/DAM-CTD-Software/ctdam/commit/0f0f4382429e43faa8dfe6c6b7ce2e42bc18b6d9))

- **deps**: Bumped action dependencies
  ([`fc59721`](https://github.com/DAM-CTD-Software/ctdam/commit/fc59721b345dded19e10fefb976321b2027226d9))

- **docs**: Setting up deployment of github pages
  ([`fc59721`](https://github.com/DAM-CTD-Software/ctdam/commit/fc59721b345dded19e10fefb976321b2027226d9))

### Documentation

- Added badges to readme ([#10](https://github.com/DAM-CTD-Software/ctdam/pull/10),
  [`fbc1bdf`](https://github.com/DAM-CTD-Software/ctdam/commit/fbc1bdf1252dbc1fe614eb7eb3dd38e92ea1a423))

- Using short title for readme ([#10](https://github.com/DAM-CTD-Software/ctdam/pull/10),
  [`fbc1bdf`](https://github.com/DAM-CTD-Software/ctdam/commit/fbc1bdf1252dbc1fe614eb7eb3dd38e92ea1a423))

### Features

- **parser**: Casts class, that handles default actions on multiple files
  ([#11](https://github.com/DAM-CTD-Software/ctdam/pull/11),
  [`a264130`](https://github.com/DAM-CTD-Software/ctdam/commit/a26413084e76bb56516b9a02af22c175110770fe))

### Testing

- Default output of test template config is a CTDData object
  ([#11](https://github.com/DAM-CTD-Software/ctdam/pull/11),
  [`a264130`](https://github.com/DAM-CTD-Software/ctdam/commit/a26413084e76bb56516b9a02af22c175110770fe))

- **conv**: Use tmp output path to avoid influencing other tests
  ([#11](https://github.com/DAM-CTD-Software/ctdam/pull/11),
  [`a264130`](https://github.com/DAM-CTD-Software/ctdam/commit/a26413084e76bb56516b9a02af22c175110770fe))

- **parser**: New test for Casts ([#11](https://github.com/DAM-CTD-Software/ctdam/pull/11),
  [`a264130`](https://github.com/DAM-CTD-Software/ctdam/commit/a26413084e76bb56516b9a02af22c175110770fe))


## v1.0.2 (2026-03-13)

### Bug Fixes

- **entry**: Updated legacy import paths in cli
  ([#6](https://github.com/DAM-CTD-Software/ctdam/pull/6),
  [`9c15371`](https://github.com/DAM-CTD-Software/ctdam/commit/9c1537174c1abe5eb07f69ea939bd1878a65a28e))

### Code Style

- **entry**: Beautified gui imports ([#6](https://github.com/DAM-CTD-Software/ctdam/pull/6),
  [`9c15371`](https://github.com/DAM-CTD-Software/ctdam/commit/9c1537174c1abe5eb07f69ea939bd1878a65a28e))

### Continuous Integration

- Add filter to prevent rerunning ci on version update
  ([#4](https://github.com/DAM-CTD-Software/ctdam/pull/4),
  [`ca2adda`](https://github.com/DAM-CTD-Software/ctdam/commit/ca2addaba73120ff59025b7e6bac614d58dea79f))

- Added changelog generation ([#4](https://github.com/DAM-CTD-Software/ctdam/pull/4),
  [`ca2adda`](https://github.com/DAM-CTD-Software/ctdam/commit/ca2addaba73120ff59025b7e6bac614d58dea79f))

- Run pypi conditionally when build artifacts exist
  ([#5](https://github.com/DAM-CTD-Software/ctdam/pull/5),
  [`a723b24`](https://github.com/DAM-CTD-Software/ctdam/commit/a723b240b2b4ec663a5e748f4cad6a9a06243ae6))


## v1.0.1 (2026-03-13)

- Initial Release

## v1.0.0 (2026-03-10)

### Changed

- Migrated from institute-wide git server to GitHub
- Migrated from Poetry to uv
- Consolidated separate repositories into one package
- Cleaned git history (removed binary files)

### Migration Notes

- Previous parser repository archived at: <https://git.iow.de/CTD-Software/seabirdfilehandler>
- Previous processor repository archived at: <https://git.iow.de/CTD-Software/processing>
- Old history preserved in backup tags
