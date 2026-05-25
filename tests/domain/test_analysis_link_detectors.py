from xseo.domain.analysis import LinkStatusRecord, detect_link_issues
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
