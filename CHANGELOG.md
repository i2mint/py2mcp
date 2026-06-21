# Changelog

All notable changes to this project are documented in this file.

The format is inspired by [Keep a Changelog](https://keepachangelog.com/);
each section corresponds to a git version tag (which is also the release
published to PyPI). Entries are commit subjects and PR titles, verbatim.

## [0.1.6] - 2026-06-17

### Fixed

- fix(http): require 'audience' for jwt auth (RFC 8707, confused-deputy defense) ([#5](https://github.com/i2mint/py2mcp/pull/5))

## [0.1.5] - 2026-06-17

### Added

- feat(http): remote Streamable-HTTP serving with OAuth 2.1 resource-server ([#4](https://github.com/i2mint/py2mcp/pull/4))

## [0.1.4] - 2026-06-17

### Added

- feat(serve): stdio runner so a capability can be packaged and launched ([#3](https://github.com/i2mint/py2mcp/pull/3))

## [0.1.3] - 2026-06-12

- ci: bump action pins (checkout@v6, setup-uv@v7)

## [0.1.2] - 2026-06-04

- Add mk_mcp_from_refs(['module:function', ...]) + public import_object ([#2](https://github.com/i2mint/py2mcp/pull/2))

## [0.1.1] - 2026-03-18

- Fix CI doctest failure and improve design
- Initial project setup with wads (uv CI, hatchling build)
