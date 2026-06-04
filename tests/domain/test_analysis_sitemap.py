from tests.domain.test_analysis_page_detectors import _page, _url
from xseo.domain.analysis.sitemap import (
    canonicalize,
    detect_sitemap_issues,
    is_sitemap_index,
    parse_sitemap_locs,
)
from xseo.domain.enums import IssueSeverity, IssueType
from xseo.domain.ids import CrawlId
from xseo.domain.urls import NormalizedUrl

URLSET = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://example.com/a</loc></url>
  <url><loc>https://example.com/b/</loc></url>
</urlset>"""

INDEX = """<?xml version="1.0" encoding="UTF-8"?>
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <sitemap><loc>https://example.com/sitemap-1.xml</loc></sitemap>
</sitemapindex>"""


def _crawl_id():
    return CrawlId.create("crawl-1").value


def _base_url():
    return NormalizedUrl.create("https://example.com/sitemap.xml").value


def _issue_types(issues):
    return {issue.issue_type for issue in issues}


def test_parse_sitemap_locs_reads_namespaced_loc_elements():
    assert parse_sitemap_locs(URLSET) == (
        "https://example.com/a",
        "https://example.com/b/",
    )


def test_is_sitemap_index_distinguishes_index_from_urlset():
    assert is_sitemap_index(INDEX) is True
    assert is_sitemap_index(URLSET) is False


def test_parse_sitemap_locs_tolerates_malformed_xml():
    assert parse_sitemap_locs("<urlset><loc>oops") == ()


def test_canonicalize_ignores_trailing_slash_and_host_case():
    assert canonicalize("https://Example.com/b/") == canonicalize(
        "https://example.com/b"
    )


def test_missing_sitemap_yields_single_site_level_issue():
    page = _page(url=_url("https://example.com/a"))

    issues = detect_sitemap_issues(
        _crawl_id(), (page,), (), sitemap_found=False, base_url=_base_url()
    )

    assert _issue_types(issues) == {IssueType.SITEMAP_MISSING}
    assert issues[0].page_id is None
    assert issues[0].severity == IssueSeverity.LOW


def test_flags_only_indexable_pages_absent_from_sitemap():
    listed = _page(url=_url("https://example.com/a"))
    # trailing-slash mismatch must still count as listed
    listed_slash = _page(url=_url("https://example.com/b"))
    missing = _page(url=_url("https://example.com/c"))
    noindex = _page(url=_url("https://example.com/secret"), robots_meta="noindex")
    not_ok = _page(url=_url("https://example.com/410"), status_code=404)

    issues = detect_sitemap_issues(
        _crawl_id(),
        (listed, listed_slash, missing, noindex, not_ok),
        ("https://example.com/a", "https://example.com/b/"),
        sitemap_found=True,
        base_url=_base_url(),
    )

    # Only the indexable, unlisted /c page is reported.
    assert _issue_types(issues) == {IssueType.PAGE_MISSING_FROM_SITEMAP}
    assert len(issues) == 1
    assert issues[0].affected_url.value == "https://example.com/c"


def test_fully_covered_sitemap_reports_nothing():
    page = _page(url=_url("https://example.com/a"))

    issues = detect_sitemap_issues(
        _crawl_id(),
        (page,),
        ("https://example.com/a",),
        sitemap_found=True,
        base_url=_base_url(),
    )

    assert issues == ()


def test_flags_sitemap_url_that_redirects():
    page = _page(
        url=_url("https://example.com/old"),
        final_url=_url("https://example.com/new"),
    )

    # List both the old and final URL so the only finding is the stale redirect,
    # not the final destination being absent from the sitemap.
    issues = detect_sitemap_issues(
        _crawl_id(),
        (page,),
        ("https://example.com/old", "https://example.com/new"),
        sitemap_found=True,
        base_url=_base_url(),
    )

    assert _issue_types(issues) == {IssueType.SITEMAP_STALE_URL}
    assert "redirects" in issues[0].explanation
    assert issues[0].severity == IssueSeverity.LOW


def test_flags_sitemap_url_that_errors():
    page = _page(url=_url("https://example.com/gone"), status_code=404)

    issues = detect_sitemap_issues(
        _crawl_id(),
        (page,),
        ("https://example.com/gone",),
        sitemap_found=True,
        base_url=_base_url(),
    )

    assert _issue_types(issues) == {IssueType.SITEMAP_STALE_URL}
    assert "404" in issues[0].explanation


def test_flags_noindex_sitemap_url():
    page = _page(url=_url("https://example.com/secret"), robots_meta="noindex")

    issues = detect_sitemap_issues(
        _crawl_id(),
        (page,),
        ("https://example.com/secret",),
        sitemap_found=True,
        base_url=_base_url(),
    )

    assert _issue_types(issues) == {IssueType.SITEMAP_STALE_URL}
    assert "noindex" in issues[0].explanation


def test_uncrawled_sitemap_url_is_not_judged_stale():
    page = _page(url=_url("https://example.com/a"))

    issues = detect_sitemap_issues(
        _crawl_id(),
        (page,),
        ("https://example.com/a", "https://example.com/never-crawled"),
        sitemap_found=True,
        base_url=_base_url(),
    )

    assert issues == ()
