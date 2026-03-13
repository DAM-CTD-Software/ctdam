# CHANGELOG

<!-- version list -->

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
