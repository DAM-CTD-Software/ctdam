# CHANGELOG

<!-- version list -->

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
