from tests.domain.test_analysis_page_detectors import _page
from xseo.domain.analysis import (
    LinkStatusRecord,
    detect_insecure_link_issues,
    detect_link_issues,
    detect_redirect_chain_issues,
)
from xseo.domain.entities import PageLink, Redirect
from xseo.domain.enums import IssueSeverity, IssueType, LinkRelation
from xseo.domain.ids import CrawlId, PageId
from xseo.domain.urls import NormalizedUrl


def _id(cls, value):
    return cls.create(value).value


def _url(value):
    return NormalizedUrl.create(value).value


def test_detects_broken_and_redirecting_internal_links():
    crawl_id = _id(CrawlId, "crawl-1")
    source_page_id = _id(PageId, "page-1")
    source_url = _url("https://example.com/source")
    broken_target = _url("https://example.com/missing")
    redirect_target = _url("https://example.com/old")

    issues = detect_link_issues(
        crawl_id,
        (
            LinkStatusRecord(
                source_page_id, source_url, broken_target, LinkRelation.INTERNAL, 404
            ),
            LinkStatusRecord(
                source_page_id, source_url, redirect_target, LinkRelation.INTERNAL, 301
            ),
            LinkStatusRecord(
                source_page_id,
                source_url,
                _url("https://outside.example.com/"),
                LinkRelation.EXTERNAL,
                404,
            ),
        ),
    )

    assert [issue.issue_type for issue in issues] == [
        IssueType.BROKEN_INTERNAL_LINK,
        IssueType.REDIRECTING_URL,
    ]
    assert [issue.severity for issue in issues] == [
        IssueSeverity.HIGH,
        IssueSeverity.LOW,
    ]


def test_flags_secure_page_linking_to_insecure_internal_url():
    page = _page(final_url=_url("https://example.com/page"))
    links = (
        PageLink(
            page.page_id,
            _url("http://example.com/insecure"),
            LinkRelation.INTERNAL,
            "insecure link",
        ),
        PageLink(
            page.page_id,
            _url("https://example.com/secure"),
            LinkRelation.INTERNAL,
            "secure link",
        ),
        PageLink(
            page.page_id,
            _url("http://other.example.com/"),
            LinkRelation.EXTERNAL,
            "external",
        ),
    )

    issues = detect_insecure_link_issues((page,), links)

    assert [issue.issue_type for issue in issues] == [
        IssueType.INSECURE_INTERNAL_LINK,
    ]
    assert issues[0].severity == IssueSeverity.MEDIUM
    assert issues[0].page_id == page.page_id
    assert "http://example.com/insecure" in issues[0].explanation


def test_insecure_link_from_non_secure_page_is_ignored():
    page = _page(final_url=_url("http://example.com/page"))
    links = (
        PageLink(
            page.page_id,
            _url("http://example.com/insecure"),
            LinkRelation.INTERNAL,
            "insecure link",
        ),
    )

    assert detect_insecure_link_issues((page,), links) == ()


def _redirect(from_url, to_url, status_code=301, crawl_id=None):
    return Redirect(
        crawl_id=crawl_id or _id(CrawlId, "crawl-1"),
        from_url=_url(from_url),
        to_url=_url(to_url),
        status_code=status_code,
    )


def test_flags_multi_hop_redirect_chain():
    crawl_id = _id(CrawlId, "crawl-1")
    redirects = (
        _redirect("https://example.com/a", "https://example.com/b"),
        _redirect("https://example.com/b", "https://example.com/c"),
    )

    issues = detect_redirect_chain_issues(crawl_id, redirects)

    assert [issue.issue_type for issue in issues] == [IssueType.REDIRECT_CHAIN]
    issue = issues[0]
    assert issue.severity == IssueSeverity.MEDIUM
    assert issue.affected_url == _url("https://example.com/a")
    assert "2 hops" in issue.explanation


def test_single_hop_redirect_is_not_a_chain():
    crawl_id = _id(CrawlId, "crawl-1")
    redirects = (_redirect("https://example.com/a", "https://example.com/b"),)

    assert detect_redirect_chain_issues(crawl_id, redirects) == ()


def test_flags_redirect_loop():
    crawl_id = _id(CrawlId, "crawl-1")
    redirects = (
        _redirect("https://example.com/a", "https://example.com/b"),
        _redirect("https://example.com/b", "https://example.com/a"),
    )

    issues = detect_redirect_chain_issues(crawl_id, redirects)

    assert [issue.issue_type for issue in issues] == [IssueType.REDIRECT_LOOP]
    assert issues[0].severity == IssueSeverity.HIGH


def test_chain_leading_into_loop_is_reported_once():
    crawl_id = _id(CrawlId, "crawl-1")
    redirects = (
        _redirect("https://example.com/start", "https://example.com/a"),
        _redirect("https://example.com/a", "https://example.com/b"),
        _redirect("https://example.com/b", "https://example.com/a"),
    )

    issues = detect_redirect_chain_issues(crawl_id, redirects)

    assert [issue.issue_type for issue in issues] == [IssueType.REDIRECT_LOOP]
    assert issues[0].affected_url == _url("https://example.com/start")


def test_no_redirects_yields_no_issues():
    assert detect_redirect_chain_issues(_id(CrawlId, "crawl-1"), ()) == ()
