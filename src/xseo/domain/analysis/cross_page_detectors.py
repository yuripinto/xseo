"""Cross-page SEO issue detectors."""

from __future__ import annotations

from collections import defaultdict

from xseo.domain.analysis.issues import build_issue
from xseo.domain.analysis.keys import normalize_comparable_text
from xseo.domain.analysis.policies import DEFAULT_SEVERITY_POLICY
from xseo.domain.enums import IssueType


def detect_duplicate_title_issues(pages, severity_policy=DEFAULT_SEVERITY_POLICY):
    return _detect_duplicate_text_issues(
        pages,
        lambda page: page.title,
        IssueType.TITLE_DUPLICATE,
        "Page title is duplicated across multiple pages.",
        severity_policy,
    )


def detect_duplicate_meta_description_issues(pages, severity_policy=DEFAULT_SEVERITY_POLICY):
    return _detect_duplicate_text_issues(
        pages,
        lambda page: page.meta_description,
        IssueType.META_DESCRIPTION_DUPLICATE,
        "Meta description is duplicated across multiple pages.",
        severity_policy,
    )


def detect_cross_page_issues(pages, severity_policy=DEFAULT_SEVERITY_POLICY):
    return (
        detect_duplicate_title_issues(pages, severity_policy)
        + detect_duplicate_meta_description_issues(pages, severity_policy)
    )


def _detect_duplicate_text_issues(pages, accessor, issue_type, explanation, severity_policy):
    groups = defaultdict(list)
    for page in pages:
        key = normalize_comparable_text(accessor(page))
        if key:
            groups[key].append(page)

    issues = []
    for comparable_key in sorted(groups):
        group = sorted(groups[comparable_key], key=lambda page: page.page_id.value)
        if len(group) < 2:
            continue
        for page in group:
            issues.append(
                build_issue(
                    page.crawl_id,
                    page.page_id,
                    page.final_url,
                    issue_type,
                    explanation,
                    severity_policy,
                    discriminator=comparable_key,
                )
            )
    return tuple(issues)
