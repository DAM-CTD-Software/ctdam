# CHANGELOG


## v2.2.0 (2026-08-24)

### Features

- **proc**: Replaced seabirdscientific in processing funktion
  ([`9b9a3e9`](https://github.com/DAM-CTD-Software/ctdam/commit/9b9a3e95706e13620908d0ee2fcbe867a6dcb7b2))


## v2.1.0 (2026-08-20)

### Features

- **proc**: Cast borders processing module
  ([`665d05c`](https://github.com/DAM-CTD-Software/ctdam/commit/665d05cb389163b85cc602940c4d44e36ae71a02))

Co-authored-by: Clara <clara-TU@MacBook-Pro-109.local>

Co-authored-by: Emil Michels <emil.michels@iow.de>


## v2.0.1 (2026-08-19)

### Bug Fixes

- Fail safe size calculation, not relying on 'scan' dim
  ([`074ad61`](https://github.com/DAM-CTD-Software/ctdam/commit/074ad61f20791a58309d1160ae333c37faea64f2))

Binning does for example not have a 'scan' dim anymore.

- Metadata provenance line during conversion and processing
  ([`d755627`](https://github.com/DAM-CTD-Software/ctdam/commit/d755627126d910163220256c1b53e07626727092))

- Return processed arrays in accessor
  ([`11e2fcb`](https://github.com/DAM-CTD-Software/ctdam/commit/11e2fcb88702a24c5090d706565198f9a696792f))

E.g. in binning, its not possible to alter the current dataset

- Set 'scan' as explicit array coordinate
  ([`2fd774e`](https://github.com/DAM-CTD-Software/ctdam/commit/2fd774e6ff29eb48385d6365bc30dab361219c26))

### Chores

- Remove python 3.11 as supported version
  ([`f419b82`](https://github.com/DAM-CTD-Software/ctdam/commit/f419b826352d4a851cfdbe7ac0acd512a7c211e9))

Dependency odf.sbe does rely on 3.12 or higher.

### Continuous Integration

- Add python 3.11-3.14 pull-request test matrix
  ([`0f7b3b2`](https://github.com/DAM-CTD-Software/ctdam/commit/0f7b3b2f923b84a19e147610d2e0582256efdb9c))

Co-authored-by: Emil Michels <emil.michels@iow.de>


## v2.0.0 (2026-08-18)

### Bug Fixes

- Circumvent hex-xmlcon mapping errors inside odf.sbe
  ([`0c21c5d`](https://github.com/DAM-CTD-Software/ctdam/commit/0c21c5d3b65423e6b33d4e25ee1272c9b2332a6a))

- Correct padding in wfilter to avoid edge effects
  ([`921acce`](https://github.com/DAM-CTD-Software/ctdam/commit/921acceb147ccb8da5e4a65fe98468e4452a4280))

- Correctly sort xarray ctd data
  ([`6761b53`](https://github.com/DAM-CTD-Software/ctdam/commit/6761b53824dde34836717deb7f6b24be3079d07a))

- Do not hide all exceptions inside processing workflows
  ([`4bc7596`](https://github.com/DAM-CTD-Software/ctdam/commit/4bc7596589eba2969d3edafac6103d66d2e7d41e))

- Generic binning using xarray-built-in-functionality
  ([`ed8e1af`](https://github.com/DAM-CTD-Software/ctdam/commit/ed8e1afcceadf50c030c25714aef354c851c615d))

- Misc small edits which surfaced with conversion and processing test
  ([`5e701e8`](https://github.com/DAM-CTD-Software/ctdam/commit/5e701e8168e662ffa1025da7a2ab48e8ab905f3a))

- Pre-check teos variable existence before calculation
  ([`efafcde`](https://github.com/DAM-CTD-Software/ctdam/commit/efafcde500689052f2a8e3efdd3987122ec3f30f))

- Processing of a single file in entry function
  ([`5de712c`](https://github.com/DAM-CTD-Software/ctdam/commit/5de712c87fd71ca6487dfa317b31cfc6f8ada66f))

- Remove obsolete accessor import that leads to circular import
  ([`a64798a`](https://github.com/DAM-CTD-Software/ctdam/commit/a64798a470c13a713ac7cd58e3e7535764b31337))

- Set time as normal data variable in bottle overview
  ([`f83d0c7`](https://github.com/DAM-CTD-Software/ctdam/commit/f83d0c7ea2dfe4be1abf3900721368dee23d2a30))

- Small fixes
  ([`6657ae0`](https://github.com/DAM-CTD-Software/ctdam/commit/6657ae0459a7913f1df0af903bb86b4d67dc3b30))

- Streamline output path handling of bottle files
  ([`5f15413`](https://github.com/DAM-CTD-Software/ctdam/commit/5f15413e213d12afb472cb5dbec2da1b85c63143))

- Use MissingParameterError consistently across processing
  ([`5046c0d`](https://github.com/DAM-CTD-Software/ctdam/commit/5046c0da712f6194fd17b0d89c78681f3a54f6ad))

- Wrong flag array inside wildedit logic
  ([`2bec032`](https://github.com/DAM-CTD-Software/ctdam/commit/2bec03277af7239158aa71c6d12f864b6c5e606e))

- **parser**: Allow empty provenance information when looking for last
  ([`2297983`](https://github.com/DAM-CTD-Software/ctdam/commit/2297983f5f2b13189c5165beeb6aab0c821dd628))

### Chores

- Added new conversion dependencies
  ([`e10eae2`](https://github.com/DAM-CTD-Software/ctdam/commit/e10eae2c92b8d2f69f4f1c35327f548e51860895))

- All low caps inside mapping file
  ([`8234d94`](https://github.com/DAM-CTD-Software/ctdam/commit/8234d94a4418f811b0dcdd46f770fdbf001b9b74))

- Remove pytest marker to run seabird binaries
  ([`090e0bd`](https://github.com/DAM-CTD-Software/ctdam/commit/090e0bd16e918939a6d000c6d6f6f89be04aa199))

- Removed conversion test file
  ([`e633d14`](https://github.com/DAM-CTD-Software/ctdam/commit/e633d14b8065c706bc18f5edb53cd0657049b122))

- Udpate coverage options
  ([`473e697`](https://github.com/DAM-CTD-Software/ctdam/commit/473e6978f0f98d4bda8e1c413b3c7aebc7ad5508))

### Code Style

- Applied ruff formatting
  ([`d3f49bc`](https://github.com/DAM-CTD-Software/ctdam/commit/d3f49bc431fb09f5cc7cd1251afe8f30803ab8ee))

- Removed unnecessary gsw_xarray imports
  ([`987ba99`](https://github.com/DAM-CTD-Software/ctdam/commit/987ba992ab8984c46bf43726b14362b1c79129c5))

### Continuous Integration

- Test settings to skip legacy tests
  ([`83f2f65`](https://github.com/DAM-CTD-Software/ctdam/commit/83f2f6512bdcbf4ee7ef6107df957796181d1269))

### Documentation

- Updated to xarray structure
  ([`b5b4872`](https://github.com/DAM-CTD-Software/ctdam/commit/b5b4872373a91cab38719f73c057c339f4cae2ba))

- **parser**: Initial docstrings
  ([`e1829cd`](https://github.com/DAM-CTD-Software/ctdam/commit/e1829cdc3fc0f992fc34fd433e22b70a3e89452e))

BREAKING CHANGE: last commit of v2-refactor

### Features

- Accessor to generate the base teos10 variables
  ([`d66dc37`](https://github.com/DAM-CTD-Software/ctdam/commit/d66dc3795b8f3f0b520f5612a1f39c669612bc6c))

- All conversion functions added
  ([`7b5ac83`](https://github.com/DAM-CTD-Software/ctdam/commit/7b5ac835790b3520531d800abfd627f028ba6c93))

- Allow empty processing module info to allow printing of metadata line
  ([`d33acf7`](https://github.com/DAM-CTD-Software/ctdam/commit/d33acf7bf0b4b9e650659b14c35cbb6553d5cfad))

- Allow path to dir in bottle log file parsing
  ([`c0a424b`](https://github.com/DAM-CTD-Software/ctdam/commit/c0a424b3b8fbac5047f11acec9551cd14bcf826d))

- Bin-state parsing
  ([`9aedf01`](https://github.com/DAM-CTD-Software/ctdam/commit/9aedf016cff25985e9c545e7d848cd8cf82d86bb))

- Export bottle file from xarray structure
  ([`fb0c093`](https://github.com/DAM-CTD-Software/ctdam/commit/fb0c093f9191a004e2f8cf554e108567c6fe54db))

- First xarray implementation for cnv files
  ([`29bcffc`](https://github.com/DAM-CTD-Software/ctdam/commit/29bcffc32bd885d314ebe620c71c810554bb9333))

- Hex to xarray conversion
  ([`2c6589d`](https://github.com/DAM-CTD-Software/ctdam/commit/2c6589db1de78bb0f7dc794358163a87e062d05b))

- High-level processing entry function
  ([`8141c51`](https://github.com/DAM-CTD-Software/ctdam/commit/8141c51252061b95630b6a974dfedaf1ca6b74f7))

- Input parsing of bl info to ctd xarray and bottle averaging
  ([`0579966`](https://github.com/DAM-CTD-Software/ctdam/commit/05799666ffca8686d2d41ac08fdcd7ab4eb53e11))

- Parse oxygen from cnv into xarray
  ([`f58ebd1`](https://github.com/DAM-CTD-Software/ctdam/commit/f58ebd10e4dd33b19f30bcecae0a283cfe81cdbd))

- Parse sample_rate to output cnv
  ([`c842483`](https://github.com/DAM-CTD-Software/ctdam/commit/c8424836510715b36af1c1f530c7dfc74225ca5a))

- Refactored metadata structure and added cnv export
  ([`25a0002`](https://github.com/DAM-CTD-Software/ctdam/commit/25a0002f6a17ccd3b67a1485bcf01c64f5409dfe))

- Restructured HexFile and XMLCONFile with new conversion methods
  ([`fa3d27f`](https://github.com/DAM-CTD-Software/ctdam/commit/fa3d27faa07aeb795ebcb0aa66c6f720d89b92cc))

- Sample rate parsing from data
  ([`9bfb5e9`](https://github.com/DAM-CTD-Software/ctdam/commit/9bfb5e961e55363ea8c967866e1b16dea468710d))

Co-authored-by: Emil Michels <emil.michels@iow.de>

- Unit conversion code
  ([`810886b`](https://github.com/DAM-CTD-Software/ctdam/commit/810886b5d4d5b79d1bba5a52d5f647beead49b04))

- Use sst2xarray parser in read_ctd_data
  ([`268ba98`](https://github.com/DAM-CTD-Software/ctdam/commit/268ba98065e18f3e074dfc202a07d1e7437989f0))

- **conv**: Hex parsing to common xarray structure
  ([`340016c`](https://github.com/DAM-CTD-Software/ctdam/commit/340016ca3bf16c08962513bc2356f95d24fd8449))

Co-authored-by: Clara Ollech <collech@gmx.de>

- **conv**: New version of hex to xarray based on ctdproc and odfsbe
  ([`d2d15fb`](https://github.com/DAM-CTD-Software/ctdam/commit/d2d15fb18ea45ba39bebe2fc1d8c74a8552535e2))

- **parser**: Adding provenance metadata after hex conversion
  ([`1e3569e`](https://github.com/DAM-CTD-Software/ctdam/commit/1e3569e5d713fda7962d3c41151dd3cd16872eeb))

- **parser**: Convert SST CTD data to xarray
  ([`7930801`](https://github.com/DAM-CTD-Software/ctdam/commit/79308017dde9eb9f079101bdd26089b5fe20f868))

- **parser**: Re-implement data gap handling in xarrays
  ([`df4c9ba`](https://github.com/DAM-CTD-Software/ctdam/commit/df4c9baad6d7dc3aef905ab77a13ba50a586a4e6))

- **proc**: Added bottle file creation processing module
  ([`cc1ff2b`](https://github.com/DAM-CTD-Software/ctdam/commit/cc1ff2b1f4c12078b72c314c4f22f1735e1f0e9d))

- **utils**: Convert lat and lon to float
  ([`b88cc4e`](https://github.com/DAM-CTD-Software/ctdam/commit/b88cc4ef436dbfe2b9eb0ebdb353af376224baab))

### Refactoring

- Bottlelogfile parsing and removed legacy parsing files
  ([`7758594`](https://github.com/DAM-CTD-Software/ctdam/commit/77585945e12c01abcc051e6897d6e1bb392bb022))

- Follow these accessor changes in module
  ([`0b11518`](https://github.com/DAM-CTD-Software/ctdam/commit/0b1151841653f9f805872a199fd800ef16c48513))

- Migrated procedure code streamlined into workflows
  ([`29aae4f`](https://github.com/DAM-CTD-Software/ctdam/commit/29aae4f2bbc2156426a25348e74148e72f1bda46))

- Moved coords and attrs creation out of cnv parsing
  ([`1389436`](https://github.com/DAM-CTD-Software/ctdam/commit/1389436f71dfc1bb8218f80d11e0d44aa6963258))

- Package import handling
  ([`cef8b7f`](https://github.com/DAM-CTD-Software/ctdam/commit/cef8b7fed36da4af2654f99149bebc64e67fed04))

- Re-add module shortcuts
  ([`361ae54`](https://github.com/DAM-CTD-Software/ctdam/commit/361ae54bad5f46b69a3638a82f8ef59b934c6e93))

- Remove legacy code
  ([`ea03c58`](https://github.com/DAM-CTD-Software/ctdam/commit/ea03c58ad166d4ecefc8dd652da782d0dd5ae31b))

- Set @property to accessor methods for easier data retrieval
  ([`d0d51a6`](https://github.com/DAM-CTD-Software/ctdam/commit/d0d51a62a5b384eba04cf4a8e0b3a9f5b364618b))

- Some restructuring of the accessor methods
  ([`011672d`](https://github.com/DAM-CTD-Software/ctdam/commit/011672d757626f6f6d48d9d1ec28a60c2942ce14))

- Tidy accessor code
  ([`396309a`](https://github.com/DAM-CTD-Software/ctdam/commit/396309aa19e784b8f6bf7eebb25b7b289a1f60d8))

- Using xarrays inside casts and visualize
  ([`7694da7`](https://github.com/DAM-CTD-Software/ctdam/commit/7694da786e6e22abfba0f4bb8be5d81d88f9db60))

- **entry**: Migrated CLI to use xarray
  ([`7e2a3b4`](https://github.com/DAM-CTD-Software/ctdam/commit/7e2a3b4805d6487ad911155eeba4a3883663100e))

- **parser**: Bottlefile using new SeabirdDataFile parent class
  ([`586337a`](https://github.com/DAM-CTD-Software/ctdam/commit/586337a91f2ffd15582e15a41a9185a76ec56efb))

- **parser**: Made xarray structure parsing more readable/debuggable
  ([`016d2b2`](https://github.com/DAM-CTD-Software/ctdam/commit/016d2b20a878a1a613452e8c1a885896d7cfb344))

- **parser**: Use parameter addition accessor inside cnv parser
  ([`13c9ccb`](https://github.com/DAM-CTD-Software/ctdam/commit/13c9ccbab3d9644af269deebf07b96a805b9f041))

- **proc**: Remove obsolete seabird processing binary calling code
  ([`eb79189`](https://github.com/DAM-CTD-Software/ctdam/commit/eb791895db8cbe46b825054053052d6817146c5c))

### Testing

- Fixed wildedit call
  ([`5ba1fff`](https://github.com/DAM-CTD-Software/ctdam/commit/5ba1fff123a1c7114938d970f7dba63c163e1a61))

- Legacy test clean up
  ([`6324d74`](https://github.com/DAM-CTD-Software/ctdam/commit/6324d7436bf6e1e2f2774510710ce01f5e078b95))

- Refactored a few test inconsistencies
  ([`e5f40fe`](https://github.com/DAM-CTD-Software/ctdam/commit/e5f40fe01ac57dc643b90dd05f191e28031392cf))

- Refactored tests
  ([`82fcd12`](https://github.com/DAM-CTD-Software/ctdam/commit/82fcd12e7283e72a4f1ffdcc5f791f60475f9ea6))

- Test file for unclassified tests
  ([`692d4f0`](https://github.com/DAM-CTD-Software/ctdam/commit/692d4f0942273e8fab0d539b96a64341b58db1a4))

- Wrong target hex number
  ([`6e12a0d`](https://github.com/DAM-CTD-Software/ctdam/commit/6e12a0de7cb6aaf6669ed3dbb2dfe08bcd22fd8b))

- **ci**: Parallelize pull request tests
  ([`4a2cd4a`](https://github.com/DAM-CTD-Software/ctdam/commit/4a2cd4aeaf524bf516e9bc68bf51f68fa2bc3ba6))

- **parser**: Use real test to check on btl file creation
  ([`2a1adb2`](https://github.com/DAM-CTD-Software/ctdam/commit/2a1adb2f7fab6a21425be4c115ebe7e9fdbdbdb7))

### Breaking Changes

- **parser**: Last commit of v2-refactor


## v1.13.2 (2026-07-23)

### Bug Fixes

- **conv**: Scantime attribute in xmlcon was not properly used during conversion
  ([`9e9dc92`](https://github.com/DAM-CTD-Software/ctdam/commit/9e9dc92d75e7bc380cc3dcb35eb7505fdc4e8a16))


## v1.13.1 (2026-07-07)

### Bug Fixes

- **parser**: Stop showing every single plot in casts
  ([`6de6007`](https://github.com/DAM-CTD-Software/ctdam/commit/6de6007d1737eeda346c5b96e8f9682f474e8e4e))

- **vis**: Favicon path not always available
  ([`b9caa43`](https://github.com/DAM-CTD-Software/ctdam/commit/b9caa438a6c33e069e57357ae6806580bb96ec2f))


## v1.13.0 (2026-07-03)

### Features

- **qc**: Added CTD quality flags and basic range and spike checks
  ([#100](https://github.com/DAM-CTD-Software/ctdam/pull/100),
  [`d160533`](https://github.com/DAM-CTD-Software/ctdam/commit/d1605334566c37c4d7147f3852c828ea8c1b4b2e))


## v1.12.0 (2026-07-03)

### Features

- **proc**: Export original Sea-Bird .btl file to disk
  ([#104](https://github.com/DAM-CTD-Software/ctdam/pull/104),
  [`deb7e7f`](https://github.com/DAM-CTD-Software/ctdam/commit/deb7e7f38706bda6ed7a5e075a30cda929f013f4))


## v1.11.0 (2026-06-29)

### Bug Fixes

- **conv**: Fix typos that were migration artifacts
  ([`6005db9`](https://github.com/DAM-CTD-Software/ctdam/commit/6005db9e5b8954316b6839bdfe9d6af5ce9446a7))

### Features

- **parser**: Added a metadata class for CTD data
  ([`e117181`](https://github.com/DAM-CTD-Software/ctdam/commit/e11718158de3b4ba9f289c179994ebf9f680aab8))

Is meant to streamline the parsing of other CTD data sources than Sea-Bird data.

- **parser**: Allow a simple list for processing module selection
  ([`bdc5d87`](https://github.com/DAM-CTD-Software/ctdam/commit/bdc5d87ac5a8da74f26181093c947bacc8dfc6cf))

- **parser**: Parser for Sea&Sun (SST) CTD data
  ([`9cfafbb`](https://github.com/DAM-CTD-Software/ctdam/commit/9cfafbb9a77d7b956a20a80c620e43b80488fd39))

### Refactoring

- **parser**: Throw more precise custom Exception on reading empty files
  ([`0082bd6`](https://github.com/DAM-CTD-Software/ctdam/commit/0082bd6eb736988b12dbc291774f8f3984d6333a))

### Testing

- **parser**: Handle non-existing files in tests
  ([`e611421`](https://github.com/DAM-CTD-Software/ctdam/commit/e611421d76fa2c860927be1d95c92c86fd8df18e))

When running parallel testing, file artifacts might lead to paths the tests are looking for, but do
  no exist any longer.


## v1.10.0 (2026-06-23)

### Features

- **conv**: Prints custom parameters from cast_borders
  ([#92](https://github.com/DAM-CTD-Software/ctdam/pull/92),
  [`900748e`](https://github.com/DAM-CTD-Software/ctdam/commit/900748e3c070f0cd8e56f59e93960f30b5799618))

### Testing

- **proc**: Updating the number of gsw functions after gsw update
  ([`296668d`](https://github.com/DAM-CTD-Software/ctdam/commit/296668d66f04c6d27c996219d286718686d00c3e))


## v1.9.0 (2026-06-22)

### Features

- **conv**: Added a soaking detection algorithm to cast_borders
  ([#91](https://github.com/DAM-CTD-Software/ctdam/pull/91),
  [`be7c20f`](https://github.com/DAM-CTD-Software/ctdam/commit/be7c20f9f165ac3b7bc0d280d280b6e5cd0ee8f7))


## v1.8.0 (2026-06-05)

### Features

- **proc**: Add interpolation option to binning
  ([#86](https://github.com/DAM-CTD-Software/ctdam/pull/86),
  [`85b9ca5`](https://github.com/DAM-CTD-Software/ctdam/commit/85b9ca597b53eeebd6e581ba56f59fa9018f07bb))

implements #53


## v1.7.0 (2026-06-05)

### Features

- **proc**: Add new loop removal
  ([`5ab90a2`](https://github.com/DAM-CTD-Software/ctdam/commit/5ab90a2956ba6fa332933fe336aaab5166986be4))

testing different approach for loop removal

implements #82

- **proc**: Implemented requested changes
  ([`5d1f219`](https://github.com/DAM-CTD-Software/ctdam/commit/5d1f2196c5f27bb4beb89be2e5edbdd0e28536dd))


## v1.6.4 (2026-06-02)

### Bug Fixes

- **conv**: Also parse unix time information to floats when converting from hex
  ([`34ddec4`](https://github.com/DAM-CTD-Software/ctdam/commit/34ddec412bf28ac7642c656d9b14ad8169f80b7a))

Following #75 where this was done for the cnv parser

### Testing

- **proc**: Skipping empty or one-line data files
  ([`6198132`](https://github.com/DAM-CTD-Software/ctdam/commit/619813252f225dcd40869573ea18ef9c43fb8584))

The current processing module interface cannot handle these data cases.


## v1.6.3 (2026-06-02)

### Bug Fixes

- **parser**: Convert timeU to float not to int
  ([`4d2ca2e`](https://github.com/DAM-CTD-Software/ctdam/commit/4d2ca2e5136af5db525e8956b3fdf7134e486be2))

Converting the unix timestamp timeU to float does not allow digits, therefore no higher time
  resolutions then one second.

### Refactoring

- **vis**: Update visualize.py
  ([`62a7f86`](https://github.com/DAM-CTD-Software/ctdam/commit/62a7f865cc49077c7538cdbd1ddbb3fc97a673b6))

- **vis**: Update visualize.py ([#74](https://github.com/DAM-CTD-Software/ctdam/pull/74),
  [`6aced3e`](https://github.com/DAM-CTD-Software/ctdam/commit/6aced3edc88de2bee4553386b5bf170c9ed0bbe0))

- add option to edit range settings live without needing to change the config.toml file - add option
  to save the new range settings - add print button to print the current figure without sidebar -
  added html icon as favicon


## v1.6.2 (2026-06-01)

### Bug Fixes

- **parser**: Replaced every occurence of '\r\n' with os.linesep which is OS-agnostic
  ([#72](https://github.com/DAM-CTD-Software/ctdam/pull/72),
  [`19ece52`](https://github.com/DAM-CTD-Software/ctdam/commit/19ece5201c62b25fdc84c51b26533634bca0ca34))


## v1.6.1 (2026-05-23)

### Bug Fixes

- **parser**: Wrong key name in binavg description output
  ([`7376b07`](https://github.com/DAM-CTD-Software/ctdam/commit/7376b073fd803ad03723344c6a7f42231c314af0))

- **proc**: Only remove loops of unbinned data
  ([`b3e01e1`](https://github.com/DAM-CTD-Software/ctdam/commit/b3e01e1c81d84c815313d2ea624a8d701a46f207))

### Testing

- Adjust tests to cnv binned with seabirds 'binavg'
  ([`a6399ae`](https://github.com/DAM-CTD-Software/ctdam/commit/a6399ae4884ffb7ece07cb0df3865405956425c5))


## v1.6.0 (2026-05-22)

### Chores

- Removal of additional newlines in pyproject.toml
  ([`a13852f`](https://github.com/DAM-CTD-Software/ctdam/commit/a13852fd475fa95a74c6b5f7c5d3fe153047a060))

### Documentation

- **parser**: Adjust docstring to reflect recent changes
  ([`c1027fa`](https://github.com/DAM-CTD-Software/ctdam/commit/c1027fa5253ec161b4e2dbae300628b42df0c543))

### Features

- **parser**: Method to cleanly remove parameters
  ([`76774d0`](https://github.com/DAM-CTD-Software/ctdam/commit/76774d021c51494c525b2fa30bbd16f55de73b95))

- **parser**: Output parsing option to create seabird-readable '.cnv'
  ([`1632ce0`](https://github.com/DAM-CTD-Software/ctdam/commit/1632ce0e7a364e9c224fff4c94b4ac1a8cd6052e))


## v1.5.3 (2026-05-20)

### Bug Fixes

- **parser**: Calculate unixtime in CnvFile
  ([`afec245`](https://github.com/DAM-CTD-Software/ctdam/commit/afec24566c45951634c13b4943255fef6453f49b))

### Refactoring

- **conv**: Unixtime timeU entry in sensor_mapping.toml
  ([`0e1ae1a`](https://github.com/DAM-CTD-Software/ctdam/commit/0e1ae1aa29a6f301343678d4182b537189e4c3ba))


## v1.5.2 (2026-05-20)

### Bug Fixes

- **conv**: More fail-save cast border end point
  ([`4f30541`](https://github.com/DAM-CTD-Software/ctdam/commit/4f305413874615b6569bbff4fda06da1022a4cc9))

### Testing

- **conv**: Updated path to comparison files converted with Sea-Birds 'datcnv'
  ([`fd4ce0d`](https://github.com/DAM-CTD-Software/ctdam/commit/fd4ce0d3cbec7af64860976c53bff3ceaf62ea5c))

Wrong legacy path that was used inside seabirdfilehandler


## v1.5.1 (2026-05-13)

### Bug Fixes

- Raise custom NoDataError if no data can be detected in Casts initialization
  ([`20a2f84`](https://github.com/DAM-CTD-Software/ctdam/commit/20a2f8428e15ec63e80a0b0f738f638e94abaf33))

- Typo in warning
  ([`3e22276`](https://github.com/DAM-CTD-Software/ctdam/commit/3e222765a84cd536110450925cc9d5dae040bb53))

### Chores

- **deps**: Use last seabirdscientific version that does not use fixed dependencies
  ([`f2b2f29`](https://github.com/DAM-CTD-Software/ctdam/commit/f2b2f293b8e5858623ebefb1377c5c37e816048a))

The ones used by seabirdscientific are so old, that for example numpy does not feature pre-built
  wheels for recent python versions.

### Documentation

- Added attribute information to Casts docstring
  ([`ca77897`](https://github.com/DAM-CTD-Software/ctdam/commit/ca77897f2e3c2d8753789ff882013e35079b7ef0))

### Refactoring

- Collected all exceptions in one central file
  ([`f1be827`](https://github.com/DAM-CTD-Software/ctdam/commit/f1be8270cc23a2cddaf01de3b87a6c2d467bf130))


## v1.5.0 (2026-05-07)

### Bug Fixes

- **parser**: Tidy Procedure import
  ([`a4eac9c`](https://github.com/DAM-CTD-Software/ctdam/commit/a4eac9c305854bfae985f0c637f4cb4de79910cf))

### Documentation

- New CTDData and contributing pages in documentation
  ([`54090be`](https://github.com/DAM-CTD-Software/ctdam/commit/54090bec39b2a1e1b752dc8ce10a4f18f97f5c79))

- Updated README with new high-level CTDData methods
  ([`66345fa`](https://github.com/DAM-CTD-Software/ctdam/commit/66345fa8a3d89153d5a1d9597f8583ab663e686b))

- **parser**: Added attributes to DataFile docstring
  ([`9036c5c`](https://github.com/DAM-CTD-Software/ctdam/commit/9036c5c34de909002587f7f7fa141987edf61980))

- **parser**: Depth calculation docstring
  ([`71a08fd`](https://github.com/DAM-CTD-Software/ctdam/commit/71a08fda3c28eed65325874733bad0bb50611834))

- **parser**: Docstrings for CTDData and processing method
  ([`e668d4f`](https://github.com/DAM-CTD-Software/ctdam/commit/e668d4fc0beb0ca8ad122e8be32f517b48de10e3))

### Features

- **parser**: Direct access to plotting functionalities in CTDData
  ([`d5ac55a`](https://github.com/DAM-CTD-Software/ctdam/commit/d5ac55aee21e9e53b3a11c4b6537e9767007e206))

### Refactoring

- **parser**: Removed unused import
  ([`a168bbb`](https://github.com/DAM-CTD-Software/ctdam/commit/a168bbb37bca6f3e34070f6774dffbeefce31b82))

### Testing

- **conv**: Tests for high-level CTDData user methods
  ([`5330c16`](https://github.com/DAM-CTD-Software/ctdam/commit/5330c16554a58213a418910f826f04bd7cf2d94f))


## v1.4.1 (2026-04-29)

### Bug Fixes

- **parser**: Also detect binned data when bin unit is 'db'
  ([`ebd107b`](https://github.com/DAM-CTD-Software/ctdam/commit/ebd107b57d8a6b5d583d0b335b59d8809b490752))

- **parser**: Do not return file info when writing cnv
  ([`370a138`](https://github.com/DAM-CTD-Software/ctdam/commit/370a138c99e58f7e88d96d90190e444255982863))

- **parser**: Give feedback when anomalous casts were detected
  ([`6f4ecc4`](https://github.com/DAM-CTD-Software/ctdam/commit/6f4ecc400853d1142fe502f505dabeaa42e58083))

- **parser**: Skip processing when only hex2py info given in Casts
  ([`d04cbfb`](https://github.com/DAM-CTD-Software/ctdam/commit/d04cbfbd332d0445e8ba1332fa19b51dbf2213c5))


## v1.4.0 (2026-04-27)

### Bug Fixes

- **parser**: Default position is 0 instead of None
  ([`5c06c11`](https://github.com/DAM-CTD-Software/ctdam/commit/5c06c1194371b28fe755cae54e01d8d173b05553))

- **proc**: General unit retrieval for new sample rate after binning
  ([`66dcbbd`](https://github.com/DAM-CTD-Software/ctdam/commit/66dcbbde9be8072ddef64a7127d7da6b3b44863a))

### Features

- Added a process function to CTDData
  ([`7d27a4b`](https://github.com/DAM-CTD-Software/ctdam/commit/7d27a4b14c7fa0f34f2ddcdb79cb38e0960cc12e))

Streamlines processing of a given data object

- **conv**: Auto-calculate depth on conversion
  ([`5e1788f`](https://github.com/DAM-CTD-Software/ctdam/commit/5e1788f1fb51232d33909520ec5ef293a214b81e))

- **parser**: Added depth calculation
  ([`2fde3f4`](https://github.com/DAM-CTD-Software/ctdam/commit/2fde3f4cff9607a1509c7f92fad8072e29d3086a))

- **proc**: Auto-calculate depth after binning
  ([`dd212ec`](https://github.com/DAM-CTD-Software/ctdam/commit/dd212ec1cb43fd4907eed5de73980cda9ceb2d0d))


## v1.3.2 (2026-04-23)

### Bug Fixes

- **proc**: Default auto-running in procedure is False
  ([`c7b7b74`](https://github.com/DAM-CTD-Software/ctdam/commit/c7b7b741e69316f3b7ef13c5615bb9bf08412edf))

Fixes Procedure(proc_settings).run('some_file') which assumes a target in proc_settings, which is
  usually only given as run() parameter.


## v1.3.1 (2026-04-21)

### Bug Fixes

- **proc**: Refactored binning to work with fixed bins that do not rely on rounding
  ([#28](https://github.com/DAM-CTD-Software/ctdam/pull/28),
  [`169b5e7`](https://github.com/DAM-CTD-Software/ctdam/commit/169b5e70f22c74e7276ff86d4fc4a19b966754ab))

### Continuous Integration

- Try to fix semantic releasing by using the complete git history
  ([#26](https://github.com/DAM-CTD-Software/ctdam/pull/26),
  [`530e7f8`](https://github.com/DAM-CTD-Software/ctdam/commit/530e7f8b683570aa878678e57c245b985f3375d6))

following https://github.com/python-semantic-release/python-semantic-release/issues/721


## v1.3.0 (2026-04-08)

### Chores

- Fix readme specification ([#22](https://github.com/DAM-CTD-Software/ctdam/pull/22),
  [`9b91dcb`](https://github.com/DAM-CTD-Software/ctdam/commit/9b91dcb2dd0a1b70f438afeda61930935ce98e9c))


## v1.2.0 (2026-03-26)

### Chores

- Reduce possible metadata errors for zenodo publishing
  ([#18](https://github.com/DAM-CTD-Software/ctdam/pull/18),
  [`72d7b9e`](https://github.com/DAM-CTD-Software/ctdam/commit/72d7b9e05ce4bc54bd557c9c60f03319554188a6))

zenodo complains about badly formatted .zenodo.json file


## v1.1.3 (2026-03-25)


## v1.1.2 (2026-03-18)

### Bug Fixes

- **entry**: Avoid circular import in procedure_config_view
  ([#13](https://github.com/DAM-CTD-Software/ctdam/pull/13),
  [`90210bd`](https://github.com/DAM-CTD-Software/ctdam/commit/90210bddd755ad913d9764d5daad68f6471e02b6))


## v1.1.1 (2026-03-18)


## v1.1.0 (2026-03-16)

### Chores

- Fixed changelog format to allow auto-updating via PSR
  ([#7](https://github.com/DAM-CTD-Software/ctdam/pull/7),
  [`63bbd73`](https://github.com/DAM-CTD-Software/ctdam/commit/63bbd73597225896a39b2d5c32b25a313fe92eda))

### Continuous Integration

- Removed test code ([#8](https://github.com/DAM-CTD-Software/ctdam/pull/8),
  [`0f0f438`](https://github.com/DAM-CTD-Software/ctdam/commit/0f0f4382429e43faa8dfe6c6b7ce2e42bc18b6d9))


## v1.0.2 (2026-03-13)

### Continuous Integration

- Run pypi conditionally when build artifacts exist
  ([#5](https://github.com/DAM-CTD-Software/ctdam/pull/5),
  [`a723b24`](https://github.com/DAM-CTD-Software/ctdam/commit/a723b240b2b4ec663a5e748f4cad6a9a06243ae6))


## v1.0.1 (2026-03-13)

### Bug Fixes

- **proc**: Handled boundary effects in wfilter
  ([`be4b8e8`](https://github.com/DAM-CTD-Software/ctdam/commit/be4b8e855c4c6d39d3d8477a6b8419e9302a39d7))

### Chores

- Added zenodo integration
  ([`6ccd6b9`](https://github.com/DAM-CTD-Software/ctdam/commit/6ccd6b9ec1c5ad93fbd9420b546d54d6d2cc002b))

- Enabled auto-updating of version in .zenodo.json
  ([`6da1150`](https://github.com/DAM-CTD-Software/ctdam/commit/6da11508f975a03575b058a3f05207d1b96f3f4c))

### Continuous Integration

- Circumvent branch protection inside ci with a dedicated github app
  ([#3](https://github.com/DAM-CTD-Software/ctdam/pull/3),
  [`4154875`](https://github.com/DAM-CTD-Software/ctdam/commit/4154875c6c7d0fda85f303d97f7c43f04f217384))

- Need to initiate sbs_data git submodule for ci tests
  ([`f360d0c`](https://github.com/DAM-CTD-Software/ctdam/commit/f360d0c104c9797cf41b5ec927f0cb06245946a7))

- **docs**: Stop auto-building docs and pushing to pages
  ([`bc9d07e`](https://github.com/DAM-CTD-Software/ctdam/commit/bc9d07ec781ddc53451422259f26ed95783684ff))

### Documentation

- Added readthedocs configuration
  ([`38988f1`](https://github.com/DAM-CTD-Software/ctdam/commit/38988f1acafc866afeb879587cdf1013cf92644a))

- Fixed ctdam installation command in uv
  ([`4f0807e`](https://github.com/DAM-CTD-Software/ctdam/commit/4f0807e8e14fb39f5aac925e51ec08e3e2e53a30))

### Testing

- **proc**: Extended test to detect unpadded filtering
  ([`f95a3fd`](https://github.com/DAM-CTD-Software/ctdam/commit/f95a3fdb11af16451a87a06d0c55441cf141e6f7))


## v1.0.0 (2026-03-11)
