# Repository Migration Notice

## Overview

On 10.03.2026, this project was migrated from separate repositories to a
unified package on GitHub.

## What Changed

### Repository Structure

- **Before**: Separate `seabirdfilehandler` and `ctd-processing` repositories, inside git.iow.de
- **After**: Single package, structured into `converter`, `parser`, `processing`, `visualization` and `cli`, here on GitHub.

### Technology Stack

- **Before**: Poetry for dependency management
- **After**: uv

### Versioning

- **Before**: Semi-automatic versioning
- **After**: Automated semantic versioning with conventional commits

### Git History

- **Before**: 1GB+ repository with deleted binaries
- **After**: Clean history starting from v1.0.0

## Old Repositories

The complete historical record is preserved:

- **seabirdfilehandler Archive**: <https://git.iow.de/CTD-Software/seabirdfilehandler>
  - Tag: `v0.14.1`
- **ctd-processing Archive**: <https://git.iow.de/CTD-Software/ctd-processing>
  - Tag: `v1.9.1`

## Version Mapping

| Old Repos                                          | New Repo |
| -------------------------------------------------- | -------- |
| seabirdfilehandler v0.14.1 + ctd-processing v1.9.1 | v1.0.0   |
