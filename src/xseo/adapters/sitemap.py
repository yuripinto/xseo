"""Sitemap fetching adapter.

Fetches ``sitemap.xml`` from a crawl's origin (following one level of
``<sitemapindex>``), then hands the raw URLs to the pure-domain coverage
detector. Any network failure is treated as "no sitemap" so a hiccup can never
fail the crawl.
"""

from __future__ import annotations

from urllib.parse import urlsplit

from xseo.domain.analysis.policies import DEFAULT_SEVERITY_POLICY
from xseo.domain.analysis.sitemap import (
    detect_sitemap_issues,
    is_sitemap_index,
    parse_sitemap_locs,
)
from xseo.domain.urls import NormalizedUrl

# Bound how many child sitemaps an index may fan out to, to keep one crawl's
# sitemap audit cheap even against pathological sitemap indexes.
_MAX_CHILD_SITEMAPS = 50


class HttpSitemapAuditor:
    def __init__(self, fetch_text, severity_policy=DEFAULT_SEVERITY_POLICY) -> None:
        self._fetch_text = fetch_text
        self._severity_policy = severity_policy

    def audit(self, crawl, pages):
        base = getattr(crawl.config.start_url, "value", crawl.config.start_url)
        parts = urlsplit(base)
        sitemap_url = f"{parts.scheme}://{parts.netloc}/sitemap.xml"

        text = self._safe_fetch(sitemap_url)
        found = text is not None
        locs: tuple[str, ...] = ()
        if found:
            if is_sitemap_index(text):
                collected: list[str] = []
                for child in parse_sitemap_locs(text)[:_MAX_CHILD_SITEMAPS]:
                    child_text = self._safe_fetch(child)
                    if child_text:
                        collected.extend(parse_sitemap_locs(child_text))
                locs = tuple(collected)
            else:
                locs = parse_sitemap_locs(text)

        base_url = NormalizedUrl.create(sitemap_url).value
        return detect_sitemap_issues(
            crawl.crawl_id,
            pages,
            locs,
            found,
            base_url,
            self._severity_policy,
        )

    def _safe_fetch(self, url):
        try:
            return self._fetch_text(url)
        except Exception:  # noqa: BLE001 - any fetch error means "no sitemap here"
            return None
