"""Single-page SEO issue detectors."""

from __future__ import annotations

from xseo.domain.analysis.issues import build_issue
from xseo.domain.analysis.policies import DEFAULT_SEVERITY_POLICY, DEFAULT_THRESHOLDS
from xseo.domain.enums import HeadingLevel, IssueType


def detect_page_issues(
    page,
    headings,
    thresholds=DEFAULT_THRESHOLDS,
    severity_policy=DEFAULT_SEVERITY_POLICY,
):
    issues = []
    title = page.title or ""
    meta_description = page.meta_description or ""

    if not title.strip():
        issues.append(
            build_issue(
                page.crawl_id,
                page.page_id,
                page.final_url,
                IssueType.TITLE_MISSING,
                "Page title is missing.",
                severity_policy,
            )
        )
    elif len(title.strip()) < thresholds.title_min:
        issues.append(
            build_issue(
                page.crawl_id,
                page.page_id,
                page.final_url,
                IssueType.TITLE_TOO_SHORT,
                f"Page title is shorter than {thresholds.title_min} characters.",
                severity_policy,
            )
        )
    elif len(title.strip()) > thresholds.title_max:
        issues.append(
            build_issue(
                page.crawl_id,
                page.page_id,
                page.final_url,
                IssueType.TITLE_TOO_LONG,
                f"Page title is longer than {thresholds.title_max} characters.",
                severity_policy,
            )
        )

    if not meta_description.strip():
        issues.append(
            build_issue(
                page.crawl_id,
                page.page_id,
                page.final_url,
                IssueType.META_DESCRIPTION_MISSING,
                "Meta description is missing.",
                severity_policy,
            )
        )
    elif len(meta_description.strip()) < thresholds.meta_description_min:
        issues.append(
            build_issue(
                page.crawl_id,
                page.page_id,
                page.final_url,
                IssueType.META_DESCRIPTION_TOO_SHORT,
                f"Meta description is shorter than {thresholds.meta_description_min} characters.",
                severity_policy,
            )
        )
    elif len(meta_description.strip()) > thresholds.meta_description_max:
        issues.append(
            build_issue(
                page.crawl_id,
                page.page_id,
                page.final_url,
                IssueType.META_DESCRIPTION_TOO_LONG,
                f"Meta description is longer than {thresholds.meta_description_max} characters.",
                severity_policy,
            )
        )

    h1s = tuple(heading for heading in headings if heading.page_id == page.page_id and heading.level == HeadingLevel.H1)
    if not h1s:
        issues.append(
            build_issue(
                page.crawl_id,
                page.page_id,
                page.final_url,
                IssueType.H1_MISSING,
                "Page has no H1 heading.",
                severity_policy,
            )
        )
    elif len(h1s) > 1:
        issues.append(
            build_issue(
                page.crawl_id,
                page.page_id,
                page.final_url,
                IssueType.H1_MULTIPLE,
                "Page has multiple H1 headings.",
                severity_policy,
            )
        )

    if page.canonical_url is not None and page.canonical_url != page.final_url:
        issues.append(
            build_issue(
                page.crawl_id,
                page.page_id,
                page.final_url,
                IssueType.CANONICAL_MISMATCH,
                "Canonical URL differs from the final page URL.",
                severity_policy,
                discriminator=page.canonical_url.value,
            )
        )

    if page.word_count.value < thresholds.thin_content_min_words:
        issues.append(
            build_issue(
                page.crawl_id,
                page.page_id,
                page.final_url,
                IssueType.THIN_CONTENT,
                f"Page has fewer than {thresholds.thin_content_min_words} words.",
                severity_policy,
            )
        )

    return tuple(issues)
