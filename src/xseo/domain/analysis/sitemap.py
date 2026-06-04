"""Sitemap coverage analysis.

Pure functions that parse a ``sitemap.xml`` payload and compare the URLs it
lists against the pages a crawl actually found. The network fetch lives in an
adapter (:mod:`xseo.adapters.sitemap`); everything here is deterministic and
unit-testable without I/O.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from urllib.parse import urlsplit, urlunsplit

from xseo.domain.analysis.issues import build_issue
from xseo.domain.analysis.policies import DEFAULT_SEVERITY_POLICY
from xseo.domain.enums import IssueType


def _local_name(tag: str) -> str:
    # Sitemaps are namespaced ("{http://…}loc"); compare on the local name.
    return tag.rsplit("}", 1)[-1].lower()


def parse_sitemap_locs(xml_text: str) -> tuple[str, ...]:
    """Return every ``<loc>`` value in a sitemap or sitemap-index document."""
    try:
        root = ET.fromstring(xml_text.strip())
    except ET.ParseError:
        return ()
    locs = []
    for element in root.iter():
        if _local_name(element.tag) == "loc" and element.text:
            text = element.text.strip()
            if text:
                locs.append(text)
    return tuple(locs)


def is_sitemap_index(xml_text: str) -> bool:
    """True when the document is a ``<sitemapindex>`` (points at more sitemaps)."""
    try:
        root = ET.fromstring(xml_text.strip())
    except ET.ParseError:
        return False
    return _local_name(root.tag) == "sitemapindex"


def canonicalize(url: str) -> str:
    """Normalize a URL for set membership: lowercase host, drop trailing slash."""
    parts = urlsplit(url)
    path = parts.path or "/"
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")
    return urlunsplit(
        (parts.scheme.lower(), parts.netloc.lower(), path, parts.query, "")
    )


def _is_indexable(page) -> bool:
    return page.status_code == 200 and "noindex" not in (page.robots_meta or "").lower()


def detect_sitemap_issues(
    crawl_id,
    pages,
    sitemap_locs,
    sitemap_found,
    base_url,
    severity_policy=DEFAULT_SEVERITY_POLICY,
):
    """Compare crawled pages against the sitemap and report coverage gaps.

    - ``sitemap_missing`` (site-level) when no sitemap was found at all.
    - ``page_missing_from_sitemap`` for each indexable page the sitemap omits.
    """
    if not sitemap_found:
        return (
            build_issue(
                crawl_id,
                None,
                base_url,
                IssueType.SITEMAP_MISSING,
                "No sitemap.xml was found at the site root.",
                severity_policy,
            ),
        )

    listed = {canonicalize(loc) for loc in sitemap_locs}
    issues = []
    for page in pages:
        if not _is_indexable(page):
            continue
        if canonicalize(page.final_url.value) not in listed:
            issues.append(
                build_issue(
                    crawl_id,
                    page.page_id,
                    page.final_url,
                    IssueType.PAGE_MISSING_FROM_SITEMAP,
                    "Indexable page is not listed in the sitemap.",
                    severity_policy,
                )
            )

    issues.extend(_detect_stale_sitemap_urls(pages, sitemap_locs, severity_policy))
    return tuple(issues)


def _detect_stale_sitemap_urls(pages, sitemap_locs, severity_policy):
    """Flag sitemap URLs that should not be there: redirects, errors, noindex.

    The inverse of ``page_missing_from_sitemap`` — a sitemap that points at
    URLs which redirect, return an error, or are noindex wastes crawl budget
    and signals staleness to search engines.
    """
    by_requested = {canonicalize(page.url.value): page for page in pages}
    by_final = {canonicalize(page.final_url.value): page for page in pages}

    issues = []
    for key in sorted({canonicalize(loc) for loc in sitemap_locs}):
        requested = by_requested.get(key)
        if requested is not None and canonicalize(requested.final_url.value) != key:
            issues.append(
                _stale_issue(
                    requested,
                    "Sitemap lists a URL that redirects; list the final "
                    "destination instead.",
                    severity_policy,
                )
            )
            continue

        page = requested or by_final.get(key)
        if page is None:
            continue  # not crawled — can't judge its freshness
        if page.status_code != 200:
            issues.append(
                _stale_issue(
                    page,
                    f"Sitemap lists a URL that returned HTTP {page.status_code}.",
                    severity_policy,
                )
            )
        elif "noindex" in (page.robots_meta or "").lower():
            issues.append(
                _stale_issue(
                    page,
                    "Sitemap lists a noindex URL, which should not be in the sitemap.",
                    severity_policy,
                )
            )
    return issues


def _stale_issue(page, explanation, severity_policy):
    return build_issue(
        page.crawl_id,
        page.page_id,
        page.url,
        IssueType.SITEMAP_STALE_URL,
        explanation,
        severity_policy,
        key_subject=page.page_id,
    )
