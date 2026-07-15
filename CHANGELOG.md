# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] — 2026-07-15

### Added
- Security headers middleware (CSP / XFO / nosniff)
- Central logging setup (`app/logging_config.py`)
- `.env.example`, `requirements-dev.txt`, `docs/ARCHITECTURE.md`
- CI: ruff lint job before multi-version pytest + Docker build
- Training cancel API; light val tuning for decision tree & random forest
- Paper-param helper on data UI; honest experiment empty states

### Changed
- Version bump to 0.3.0
- Settings store only active keys (seed / ratios / defaults)
- Portable relative paths in metrics and export metadata
- Makefile targets for lint/dev

### Security
- Optional `PROXYGUARD_TOKEN` for write APIs
- Upload size/type limits; reject NaN/Inf features

## [0.2.4] — 2026-07-15

### Added
- Defense-demo UX: cancel train, progress messages, RF val n_estimators
- `/api/predict/stats`, `/api/system`

## [0.2.0] — 2026-07-15

### Added
- GitHub packaging: badges, diagrams, LICENSE, CONTRIBUTING, SECURITY
- Docker / Compose, issue & PR templates
- pyproject.toml, editorconfig, CITATION.cff

## [0.1.0] — 2026-07-11

### Added
- FastAPI console: data / train / predict / experiments / settings
- Synthetic 17-D features, 8-model zoo, offline suite, offline runners

[0.3.0]: https://github.com/ibi6/ProxyGuard-ML/compare/v0.2.4...v0.3.0
[0.2.4]: https://github.com/ibi6/ProxyGuard-ML/compare/v0.2.0...v0.2.4
[0.2.0]: https://github.com/ibi6/ProxyGuard-ML/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/ibi6/ProxyGuard-ML/releases/tag/v0.1.0
