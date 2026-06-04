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

    h1s = tuple(
        heading
        for heading in headings
        if heading.page_id == page.page_id and heading.level == HeadingLevel.H1
    )
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

    if page.content_length > thresholds.page_size_max_bytes:
        issues.append(
            build_issue(
                page.crawl_id,
                page.page_id,
                page.final_url,
                IssueType.PAGE_TOO_LARGE,
                f"Page HTML is larger than {thresholds.page_size_max_bytes} bytes.",
                severity_policy,
            )
        )

    if "noindex" in (page.robots_meta or "").lower():
        issues.append(
            build_issue(
                page.crawl_id,
                page.page_id,
                page.final_url,
                IssueType.NOINDEX_PAGE,
                "Page is marked noindex and will be excluded from search results.",
                severity_policy,
            )
        )

    if page.images_missing_alt > 0:
        issues.append(
            build_issue(
                page.crawl_id,
                page.page_id,
                page.final_url,
                IssueType.IMAGES_MISSING_ALT,
                f"{page.images_missing_alt} of {page.image_count} images are missing alt text.",
                severity_policy,
            )
        )

    if not page.has_viewport:
        issues.append(
            build_issue(
                page.crawl_id,
                page.page_id,
                page.final_url,
                IssueType.MISSING_VIEWPORT,
                "Page has no responsive viewport meta tag.",
                severity_policy,
            )
        )

    if not page.has_lang:
        issues.append(
            build_issue(
                page.crawl_id,
                page.page_id,
                page.final_url,
                IssueType.MISSING_LANG,
                "Page has no lang attribute on the <html> element.",
                severity_policy,
            )
        )

    if not page.has_charset:
        issues.append(
            build_issue(
                page.crawl_id,
                page.page_id,
                page.final_url,
                IssueType.MISSING_CHARSET,
                "Page declares no character encoding.",
                severity_policy,
            )
        )

    if page.mixed_content_count > 0:
        issues.append(
            build_issue(
                page.crawl_id,
                page.page_id,
                page.final_url,
                IssueType.MIXED_CONTENT,
                f"{page.mixed_content_count} resources are loaded over http on an "
                "https page; browsers may block them.",
                severity_policy,
            )
        )

    if not page.has_open_graph:
        issues.append(
            build_issue(
                page.crawl_id,
                page.page_id,
                page.final_url,
                IssueType.OPEN_GRAPH_MISSING,
                "Page has no Open Graph tags, so social shares lack a rich preview.",
                severity_policy,
            )
        )

    if not page.has_structured_data:
        issues.append(
            build_issue(
                page.crawl_id,
                page.page_id,
                page.final_url,
                IssueType.STRUCTURED_DATA_MISSING,
                "Page has no JSON-LD structured data for rich search results.",
                severity_policy,
            )
        )

    return tuple(issues)
