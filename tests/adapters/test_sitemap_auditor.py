from types import SimpleNamespace

from tests.domain.test_analysis_page_detectors import _page, _url
from xseo.adapters.sitemap import HttpSitemapAuditor
from xseo.domain.enums import IssueType
from xseo.domain.ids import CrawlId

URLSET = """<?xml version="1.0"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/a</loc></url>
</urlset>"""

INDEX = """<?xml version="1.0"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap><loc>https://example.com/sitemap-1.xml</loc></sitemap>
</sitemapindex>"""

CHILD = """<?xml version="1.0"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/a</loc></url>
</urlset>"""


def _crawl():
    return SimpleNamespace(
        crawl_id=CrawlId.create("crawl-1").value,
        config=SimpleNamespace(start_url=SimpleNamespace(value="https://example.com/")),
    )


def _fetcher(mapping):
    return lambda url: mapping.get(url)


def _issue_types(issues):
    return {i.issue_type for i in issues}


def test_audit_flags_pages_absent_from_a_found_sitemap():
    pages = (
        _page(url=_url("https://example.com/a")),
        _page(url=_url("https://example.com/b")),
    )
    auditor = HttpSitemapAuditor(_fetcher({"https://example.com/sitemap.xml": URLSET}))

    issues = auditor.audit(_crawl(), pages)

    assert _issue_types(issues) == {IssueType.PAGE_MISSING_FROM_SITEMAP}
    assert issues[0].affected_url.value == "https://example.com/b"


def test_audit_follows_a_sitemap_index_one_level():
    pages = (_page(url=_url("https://example.com/a")),)
    auditor = HttpSitemapAuditor(
        _fetcher(
            {
                "https://example.com/sitemap.xml": INDEX,
                "https://example.com/sitemap-1.xml": CHILD,
            }
        )
    )

    # /a is listed via the child sitemap, so nothing is flagged.
    assert auditor.audit(_crawl(), pages) == ()


def test_audit_reports_missing_sitemap_when_fetch_returns_none():
    auditor = HttpSitemapAuditor(_fetcher({}))

    issues = auditor.audit(_crawl(), (_page(url=_url("https://example.com/a")),))

    assert _issue_types(issues) == {IssueType.SITEMAP_MISSING}


def test_audit_treats_fetch_errors_as_missing_sitemap():
    def boom(url):
        raise RuntimeError("network down")

    auditor = HttpSitemapAuditor(boom)

    issues = auditor.audit(_crawl(), (_page(url=_url("https://example.com/a")),))

    assert _issue_types(issues) == {IssueType.SITEMAP_MISSING}
