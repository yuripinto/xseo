"""Tests for report building, rendering, and diffing."""

from __future__ import annotations

import json
from dataclasses import dataclass
from types import SimpleNamespace

from xseo import reporting
from xseo.application.read_models import DuplicateGroupRow, IssueRow, PageRow
from xseo.domain.enums import IssueSeverity, IssueType


@dataclass(frozen=True)
class _Url:
    value: str


def _state():
    return SimpleNamespace(
        issues=(
            IssueRow(
                issue_id="i1",
                affected_url="https://example.com/a",
                issue_type=IssueType.BROKEN_INTERNAL_LINK,
                severity=IssueSeverity.HIGH,
                explanation="Link is broken <oops>",
            ),
            IssueRow(
                issue_id="i2",
                affected_url="https://example.com/b",
                issue_type=IssueType.THIN_CONTENT,
                severity=IssueSeverity.LOW,
                explanation="Too few words",
            ),
        ),
        pages=(
            PageRow(
                page_id="p1",
                url=_Url("https://example.com/a"),
                final_url=_Url("https://example.com/a"),
                status_code=200,
                title="A",
                meta_description=None,
                canonical_url=None,
                word_count=10,
            ),
        ),
        duplicate_groups=(
            DuplicateGroupRow(
                duplicate_group_id="g1",
                content_hash="abc",
                page_count=2,
                representative_url=_Url("https://example.com/dup"),
            ),
        ),
        last_error=None,
    )


def test_build_report_shape():
    report = reporting.build_report(_state(), "https://example.com/")
    assert report["crawl"]["pages_crawled"] == 1
    assert report["crawl"]["issues_found"] == 2
    assert report["summary"]["by_severity"] == {"high": 1, "low": 1}


def test_render_html_escapes_and_is_self_contained():
    report = reporting.build_report(_state(), "https://example.com/")
    out = reporting.render_html(report)
    assert out.lstrip().startswith("<!doctype html>")
    # User-controlled text must be escaped, not injected raw.
    assert "<oops>" not in out
    assert "&lt;oops&gt;" in out
    # No external assets — everything inline.
    assert "http-equiv" not in out
    assert "<link" not in out


def test_render_sarif_is_valid_json_with_levels():
    report = reporting.build_report(_state(), "https://example.com/")
    log = json.loads(reporting.render_sarif(report))
    assert log["version"] == "2.1.0"
    results = log["runs"][0]["results"]
    assert len(results) == 2
    levels = {r["ruleId"]: r["level"] for r in results}
    assert levels["broken_internal_link"] == "error"
    assert levels["thin_content"] == "note"


def test_diff_detects_new_and_fixed():
    base = reporting.build_report(_state(), "https://example.com/")
    # head: drop the thin-content issue, add a new medium issue.
    head = {
        "crawl": {"issues_found": 2, "start_url": "https://example.com/"},
        "issues": [
            {
                "severity": "high",
                "type": "broken_internal_link",
                "url": "https://example.com/a",
                "explanation": "Link is broken",
            },
            {
                "severity": "medium",
                "type": "h1_missing",
                "url": "https://example.com/c",
                "explanation": "No H1",
            },
        ],
    }
    diff = reporting.diff_reports(base, head)
    assert [i["type"] for i in diff["new_issues"]] == ["h1_missing"]
    assert [i["type"] for i in diff["fixed_issues"]] == ["thin_content"]
    assert diff["unchanged"] == 1
