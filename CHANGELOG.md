# CHANGELOG


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
