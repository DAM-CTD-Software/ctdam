# CHANGELOG


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
