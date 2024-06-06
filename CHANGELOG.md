# Changelog

All notable changes to this project will be documented in this file.

- ##### The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
- ##### This project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Ability to discover live nodes via connecting to a node explorer backend via an `API_URL`. Since there is no public backend deployment yet, this option is only available to the Ritual team.
- Allows routing to explicitly specified nodes (via `ips.txt`), nodes discovered via the node explorer (`API_URL`), or both.
- New `containers/` endpoint for container discovery across all nodes monitored by the router.

### Security
- Bumped `aiohttp` version to `3.9.4`.

## [0.1.0] - 2024-01-18

### Added
- Initial release of Infernet Router.
