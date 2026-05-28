# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0](https://github.com/yuripinto/xseo/compare/v0.1.0...v0.2.0) (2026-05-28)


### Features

* distribute prebuilt binaries and publish to PyPI ([#2](https://github.com/yuripinto/xseo/issues/2)) ([1395068](https://github.com/yuripinto/xseo/commit/13950684bac71f926ada090e002739e2849f07ce))

## [0.1.0] - 2026-05-27

Initial public release.

### Added

- Desktop UI (PySide6) with a threaded background worker that keeps crawling
  responsive and streams live progress.
- Polite crawler that respects `robots.txt` and applies a configurable
  per-request delay, with same-host scoping and a page limit.
- On-page extraction of titles, meta descriptions, headings, canonicals,
  robots directives, and internal/external links via `selectolax`.
- Single-page issue detection: missing/short/long titles and meta
  descriptions, missing/multiple H1s, canonical mismatch, and thin content.
- Cross-page issue detection: duplicate titles and meta descriptions.
- Internal link checks: broken links (4xx/5xx) and redirecting URLs (3xx).
- Exact duplicate-content detection through content hashing and grouped
  read models.
- Sortable tables for pages, issues, and duplicate groups, plus a
  double-click page detail dialog.
- CSV export for every result view.
- Local persistence in SQLite at `~/.xseo/xseo.sqlite3`, restoring the last
  crawl on launch.
- CI on GitHub Actions (ruff lint/format + pytest across Linux, macOS, and
  Windows) and a 145-test suite covering domain, adapters, integration,
  property-based, and UI smoke tests.

[0.1.0]: https://github.com/yuripinto/xseo/releases/tag/v0.1.0
