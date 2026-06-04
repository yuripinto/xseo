"""Tests for the headless CLI.

Two layers: fast unit tests for the CI-critical pure logic (exit codes, report
shape, argument parsing), and one end-to-end test that runs a real crawl against
a local HTTP server serving the HTML fixtures.
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace

import pytest

from xseo.application.read_models import DuplicateGroupRow, IssueRow, PageRow
from xseo.cli import _build_parser, _build_report, _exit_code, main
from xseo.domain.enums import IssueSeverity, IssueType

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "site"


def _issue(severity, issue_type, url="https://example.com/"):
    return IssueRow(
        issue_id="i",
        affected_url=url,
        issue_type=issue_type,
        severity=severity,
        explanation="example",
    )


def _state(issues=(), pages=(), duplicate_groups=()):
    return SimpleNamespace(
        issues=tuple(issues),
        pages=tuple(pages),
        duplicate_groups=tuple(duplicate_groups),
        last_error=None,
    )


# --- pure logic ------------------------------------------------------------


def test_exit_code_none_always_passes():
    issues = [_issue(IssueSeverity.HIGH, IssueType.BROKEN_INTERNAL_LINK)]
    assert _exit_code(issues, "none") == 0


def test_exit_code_fails_at_or_above_threshold():
    issues = [_issue(IssueSeverity.MEDIUM, IssueType.H1_MISSING)]
    assert _exit_code(issues, "medium") == 1
    assert _exit_code(issues, "high") == 0


def test_exit_code_passes_when_no_issues():
    assert _exit_code([], "low") == 0


def test_build_report_counts_and_unwraps_value_objects():
    @dataclass(frozen=True)
    class _Url:
        value: str

    state = _state(
        issues=[
            _issue(IssueSeverity.HIGH, IssueType.BROKEN_INTERNAL_LINK),
            _issue(IssueSeverity.LOW, IssueType.THIN_CONTENT),
            _issue(IssueSeverity.LOW, IssueType.THIN_CONTENT),
        ],
        pages=[
            PageRow(
                page_id="p1",
                url=_Url("https://example.com/"),
                final_url=_Url("https://example.com/"),
                status_code=200,
                title="Home",
                meta_description=None,
                canonical_url=None,
                word_count=12,
            )
        ],
        duplicate_groups=[
            DuplicateGroupRow(
                duplicate_group_id="g1",
                content_hash="abc",
                page_count=2,
                representative_url=_Url("https://example.com/dup"),
            )
        ],
    )
    report = _build_report(state, SimpleNamespace(url="https://example.com/"))

    assert report["crawl"]["issues_found"] == 3
    assert report["summary"]["by_severity"] == {"high": 1, "low": 2}
    assert report["summary"]["by_type"]["thin_content"] == 2
    assert report["pages"][0]["url"] == "https://example.com/"
    assert (
        report["duplicate_groups"][0]["representative_url"] == "https://example.com/dup"
    )


def test_parser_defaults():
    args = _build_parser().parse_args(["crawl", "https://example.com/"])
    assert args.command == "crawl"
    assert args.limit == 500
    assert args.delay == 0.5
    assert args.fail_on == "none"
    assert args.format == "json"
    assert args.all_hosts is False
    assert args.no_robots is False


def test_parser_diff_subcommand():
    args = _build_parser().parse_args(["diff", "base.json", "head.json"])
    assert args.command == "diff"
    assert args.base == "base.json"
    assert args.head == "head.json"
    assert args.fail_on_new == "none"


def test_diff_command_fails_on_new(tmp_path, capsys):
    base = tmp_path / "base.json"
    head = tmp_path / "head.json"
    base.write_text(
        json.dumps({"crawl": {"issues_found": 0}, "issues": []}), encoding="utf-8"
    )
    head.write_text(
        json.dumps(
            {
                "crawl": {"issues_found": 1},
                "issues": [
                    {
                        "severity": "high",
                        "type": "broken_internal_link",
                        "url": "https://example.com/x",
                        "explanation": "broken",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    assert main(["diff", str(base), str(head), "--fail-on-new", "high"]) == 1
    assert main(["diff", str(base), str(head), "--fail-on-new", "none"]) == 0


# --- end to end ------------------------------------------------------------


@pytest.fixture
def live_site():
    handler = partial(SimpleHTTPRequestHandler, directory=str(FIXTURES))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}/"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_crawl_end_to_end_writes_report(tmp_path, live_site):
    report_path = tmp_path / "report.json"
    code = main(
        [
            "crawl",
            live_site,
            "--db",
            str(tmp_path / "cli.sqlite3"),
            "--no-robots",
            "--delay",
            "0",
            "--out",
            str(report_path),
        ]
    )

    assert code == 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["crawl"]["pages_crawled"] >= 1
    assert report["crawl"]["start_url"] == live_site
    assert "by_severity" in report["summary"]


def test_crawl_html_and_sarif_formats(tmp_path, live_site):
    db = str(tmp_path / "cli.sqlite3")
    html_path = tmp_path / "report.html"
    sarif_path = tmp_path / "report.sarif"

    assert (
        main(
            [
                "crawl",
                live_site,
                "--db",
                db,
                "--no-robots",
                "--delay",
                "0",
                "--format",
                "html",
                "--out",
                str(html_path),
            ]
        )
        == 0
    )
    assert html_path.read_text(encoding="utf-8").lstrip().startswith("<!doctype html>")

    assert (
        main(
            [
                "crawl",
                live_site,
                "--db",
                db,
                "--no-robots",
                "--delay",
                "0",
                "--format",
                "sarif",
                "--out",
                str(sarif_path),
            ]
        )
        == 0
    )
    log = json.loads(sarif_path.read_text(encoding="utf-8"))
    assert log["version"] == "2.1.0"
    assert log["runs"][0]["tool"]["driver"]["name"] == "xseo"


def test_crawl_fail_on_low_returns_nonzero(tmp_path, live_site):
    # The fixture home page has a cross-host canonical, thin content, and no
    # viewport/charset, so at least one low-or-higher issue is always present.
    code = main(
        [
            "crawl",
            live_site,
            "--db",
            str(tmp_path / "cli.sqlite3"),
            "--no-robots",
            "--delay",
            "0",
            "--fail-on",
            "low",
        ]
    )
    assert code == 1
