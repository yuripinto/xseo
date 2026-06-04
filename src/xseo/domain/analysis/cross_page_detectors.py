"""Cross-page SEO issue detectors."""

from __future__ import annotations

from collections import defaultdict
from urllib.parse import urlsplit

from xseo.domain.analysis.issues import build_issue
from xseo.domain.analysis.keys import normalize_comparable_text
from xseo.domain.analysis.policies import DEFAULT_SEVERITY_POLICY
from xseo.domain.analysis.sitemap import canonicalize
from xseo.domain.enums import IssueType


def detect_duplicate_title_issues(pages, severity_policy=DEFAULT_SEVERITY_POLICY):
    return _detect_duplicate_text_issues(
        pages,
        lambda page: page.title,
        IssueType.TITLE_DUPLICATE,
        "Page title is duplicated across multiple pages.",
        severity_policy,
    )


def detect_duplicate_meta_description_issues(
    pages, severity_policy=DEFAULT_SEVERITY_POLICY
):
    return _detect_duplicate_text_issues(
        pages,
        lambda page: page.meta_description,
        IssueType.META_DESCRIPTION_DUPLICATE,
        "Meta description is duplicated across multiple pages.",
        severity_policy,
    )


def detect_cross_page_issues(pages, severity_policy=DEFAULT_SEVERITY_POLICY):
    return detect_duplicate_title_issues(
        pages, severity_policy
    ) + detect_duplicate_meta_description_issues(pages, severity_policy)


def detect_canonical_target_issues(pages, severity_policy=DEFAULT_SEVERITY_POLICY):
    """Flag canonicals that point somewhere a canonical should never point.

    ``canonical_mismatch`` already covers "canonical differs from the page URL".
    This resolves the *target* of a non-self canonical against the crawled pages
    and reports when it leads to:

    - ``canonical_to_noindex`` — a page excluded from the index (the canonical
      consolidates signals onto a URL that will never rank).
    - ``canonical_to_redirect`` — a redirecting URL (the canonical should be the
      final destination, not a hop).
    - ``canonical_cross_domain`` — a different host (rarely intentional; usually
      a templating bug).
    """
    pages_by_url = {}
    for page in pages:
        pages_by_url.setdefault(canonicalize(page.final_url.value), page)

    issues = []
    for page in pages:
        canonical = page.canonical_url
        if canonical is None:
            continue
        if canonicalize(canonical.value) == canonicalize(page.final_url.value):
            continue  # self-referential canonical is the healthy case

        if _host(canonical.value) != _host(page.final_url.value):
            issues.append(
                _canonical_issue(
                    page,
                    canonical,
                    IssueType.CANONICAL_CROSS_DOMAIN,
                    "Canonical URL points to a different domain.",
                    severity_policy,
                )
            )
            continue

        target = pages_by_url.get(canonicalize(canonical.value))
        if target is None:
            continue
        if "noindex" in (target.robots_meta or "").lower():
            issues.append(
                _canonical_issue(
                    page,
                    canonical,
                    IssueType.CANONICAL_TO_NOINDEX,
                    "Canonical URL points to a noindex page, so its ranking "
                    "signals are consolidated onto a URL that will not be indexed.",
                    severity_policy,
                )
            )
        elif 300 <= target.status_code <= 399:
            issues.append(
                _canonical_issue(
                    page,
                    canonical,
                    IssueType.CANONICAL_TO_REDIRECT,
                    "Canonical URL points to a redirecting URL instead of the "
                    "final destination.",
                    severity_policy,
                )
            )
    return tuple(issues)


def _canonical_issue(page, canonical, issue_type, explanation, severity_policy):
    return build_issue(
        page.crawl_id,
        page.page_id,
        page.final_url,
        issue_type,
        explanation,
        severity_policy,
        discriminator=canonical.value,
        key_subject=page.page_id,
    )


def _host(url):
    return urlsplit(url).netloc.lower()


def _detect_duplicate_text_issues(
    pages, accessor, issue_type, explanation, severity_policy
):
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
