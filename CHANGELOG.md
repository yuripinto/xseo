# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.6.0](https://github.com/yuripinto/xseo/compare/v0.5.0...v0.6.0) (2026-06-04)


### Features

* audit sitemap.xml coverage during a crawl ([#21](https://github.com/yuripinto/xseo/issues/21)) ([a306c28](https://github.com/yuripinto/xseo/commit/a306c28a5429a688ed3abfb7996290f6cfa285fc))
* detect hreflang clusters that are not self-referential ([#19](https://github.com/yuripinto/xseo/issues/19)) ([e87a27e](https://github.com/yuripinto/xseo/commit/e87a27e14a87b34ad76f5bcb82045463329f105a))

## [0.5.0](https://github.com/yuripinto/xseo/compare/v0.4.0...v0.5.0) (2026-06-04)


### Features

* add HTML and SARIF report formats, a crawl-diff command, and a GitHub Action ([#14](https://github.com/yuripinto/xseo/issues/14)) ([9b3d6e0](https://github.com/yuripinto/xseo/commit/9b3d6e032d87060255c6125cf8f95e523eb7e7a7))
* detect mixed content, missing Open Graph, and missing structured data ([#15](https://github.com/yuripinto/xseo/issues/15)) ([b711493](https://github.com/yuripinto/xseo/commit/b711493934a5422e8543b96c84bbb5d54bd49224))


### Documentation

* lead with both desktop and CLI in the README intro ([#16](https://github.com/yuripinto/xseo/issues/16)) ([da30f52](https://github.com/yuripinto/xseo/commit/da30f528089e2eb8e79b2eec2a8394d5bab5c544))

## [0.4.0](https://github.com/yuripinto/xseo/compare/v0.3.0...v0.4.0) (2026-06-04)


### Features

* add a headless CLI for crawling and CI gating ([#12](https://github.com/yuripinto/xseo/issues/12)) ([2966aa1](https://github.com/yuripinto/xseo/commit/2966aa18f19f65792eab57b2d2c9e1d76688df29))

## [0.3.0](https://github.com/yuripinto/xseo/compare/v0.2.0...v0.3.0) (2026-06-03)


### Features

* detect images missing alt text ([#10](https://github.com/yuripinto/xseo/issues/10)) ([578361f](https://github.com/yuripinto/xseo/commit/578361f556e69ad9b13848d9356ff5aaeb1b1154))
* detect missing viewport, lang, and charset declarations ([#11](https://github.com/yuripinto/xseo/issues/11)) ([18bb892](https://github.com/yuripinto/xseo/commit/18bb892180a357709a39942f74e99132d50bc96b))
* detect oversized pages, noindex pages, and insecure internal links ([#8](https://github.com/yuripinto/xseo/issues/8)) ([1a0678a](https://github.com/yuripinto/xseo/commit/1a0678a1d75fe5a6ae2c58ec012440f1bdcf6436))


### Documentation

* add a live crawl demo gif to the top of the README ([#7](https://github.com/yuripinto/xseo/issues/7)) ([9a79a69](https://github.com/yuripinto/xseo/commit/9a79a697410f029a7f7ddaeaa06c6c08a5e9140b))
* add direct per-OS download links to the README ([#4](https://github.com/yuripinto/xseo/issues/4)) ([55a8001](https://github.com/yuripinto/xseo/commit/55a8001bd6b42cc7c8f6490ffa2fa87f8a793a2a))

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
