# Contributing to xseo

Thanks for your interest in improving `xseo`! This is a small, local-first
desktop SEO crawler and contributions of all sizes are welcome — bug reports,
fixes, new SEO checks, docs, and tests.

## Development setup

`xseo` targets **Python 3.12+**. Clone the repo and install it in editable mode
with the test and dev extras:

```bash
python3 -m pip install -e '.[test,dev]'
```

This pulls in `pytest`, `hypothesis`, and `pytest-qt` (tests) plus `ruff`
(lint/format).

## Running the app

```bash
xseo-ui
# or, from the source tree:
python3 -m xseo.ui.app
```

The UI stores its SQLite database at `~/.xseo/xseo.sqlite3`.

## Running the checks

Please make sure all three pass before opening a pull request — they are the
same checks CI runs:

```bash
ruff check src tests          # lint
ruff format --check src tests  # formatting
python3 -m pytest -q           # tests (Qt runs headless via QT_QPA_PLATFORM=offscreen in CI)
```

To auto-fix lint issues and apply formatting:

```bash
ruff check --fix src tests
ruff format src tests
```

UI tests run headless in CI. Locally, if you hit Qt display errors, prefix the
test command with `QT_QPA_PLATFORM=offscreen`.

## Project layout

The codebase follows a hexagonal (ports & adapters) architecture — keep the
dependency direction pointing inward (UI → application → domain):

```
src/xseo/
├── domain/         # entities, value objects, ports, crawl engine, analysis — no I/O
├── application/    # services, commands, queries, read models
├── adapters/       # HTTP, persistence, export, background worker, robots.txt
└── ui/             # PySide6 app, widgets, controller
```

When adding behavior, prefer putting pure logic in `domain/` behind a port and
the I/O in an `adapters/` implementation, mirroring the existing structure
(e.g. `RobotsPolicyPort` in the domain, `RobotsTxtPolicy` in adapters).

## Commit and PR conventions

- Use [Conventional Commits](https://www.conventionalcommits.org/) for commit
  messages (`feat:`, `fix:`, `chore:`, `docs:`, `test:`, `ci:`, …).
- Keep PRs focused; include tests for behavior changes.
- Describe the *why* in the PR body, not just the *what*.

## Reporting bugs and requesting features

Open an issue using the templates under
[`.github/ISSUE_TEMPLATE`](.github/ISSUE_TEMPLATE). For bugs, include the steps
to reproduce, what you expected, and what happened instead.
