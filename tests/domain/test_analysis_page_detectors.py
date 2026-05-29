from xseo.domain.analysis import detect_page_issues
from xseo.domain.entities import ExtractedPage, Heading
from xseo.domain.enums import HeadingLevel, IssueSeverity, IssueType
from xseo.domain.ids import CrawlId, PageId
from xseo.domain.urls import NormalizedUrl
from xseo.domain.value_objects import ContentHash, WordCount


def _id(cls, value):
    return cls.create(value).value


def _url(value):
    return NormalizedUrl.create(value).value


def _page(**overrides):
    crawl_id = overrides.pop("crawl_id", _id(CrawlId, "crawl-1"))
    page_id = overrides.pop("page_id", _id(PageId, "page-1"))
    url = overrides.pop("url", _url("https://example.com/page"))
    values = {
        "page_id": page_id,
        "crawl_id": crawl_id,
        "url": url,
        "final_url": overrides.pop("final_url", url),
        "status_code": 200,
        "content_type": "text/html",
        "title": "A Useful Search Result Title Example",
        "meta_description": "A useful search result description with enough detail for readers and search engines.",
        "canonical_url": None,
        "robots_meta": None,
        "word_count": WordCount.create(250).value,
        "content_length": 2048,
        "content_hash": ContentHash.create("abc12345").value,
    }
    values.update(overrides)
    return ExtractedPage(**values)


def _h1(page, position=1):
    return Heading(
        page_id=page.page_id,
        level=HeadingLevel.H1,
        text="Main heading",
        position=position,
    )


def _issue_types(issues):
    return {issue.issue_type for issue in issues}


def test_detects_missing_title_meta_h1_and_thin_content():
    page = _page(
        title=" ", meta_description=None, word_count=WordCount.create(42).value
    )

    issues = detect_page_issues(page, headings=())

    assert _issue_types(issues) == {
        IssueType.TITLE_MISSING,
        IssueType.META_DESCRIPTION_MISSING,
        IssueType.H1_MISSING,
        IssueType.THIN_CONTENT,
    }
    assert {issue.severity for issue in issues} == {
        IssueSeverity.MEDIUM,
        IssueSeverity.LOW,
    }


def test_detects_title_and_meta_threshold_issues():
    short = _page(title="Short", meta_description="short description")
    long = _page(
        page_id=_id(PageId, "page-2"),
        url=_url("https://example.com/long"),
        title="T" * 61,
        meta_description="M" * 161,
    )

    short_issues = detect_page_issues(short, headings=(_h1(short),))
    long_issues = detect_page_issues(long, headings=(_h1(long),))

    assert IssueType.TITLE_TOO_SHORT in _issue_types(short_issues)
    assert IssueType.META_DESCRIPTION_TOO_SHORT in _issue_types(short_issues)
    assert IssueType.TITLE_TOO_LONG in _issue_types(long_issues)
    assert IssueType.META_DESCRIPTION_TOO_LONG in _issue_types(long_issues)


def test_detects_multiple_h1_and_canonical_mismatch():
    final_url = _url("https://example.com/page")
    canonical_url = _url("https://example.com/canonical")
    page = _page(final_url=final_url, canonical_url=canonical_url)

    issues = detect_page_issues(page, headings=(_h1(page, 1), _h1(page, 2)))

    assert IssueType.H1_MULTIPLE in _issue_types(issues)
    assert IssueType.CANONICAL_MISMATCH in _issue_types(issues)
    canonical_issue = next(
        issue for issue in issues if issue.issue_type == IssueType.CANONICAL_MISMATCH
    )
    assert canonical_issue.severity == IssueSeverity.HIGH


def test_valid_page_has_no_page_level_issues():
    page = _page()

    assert detect_page_issues(page, headings=(_h1(page),)) == ()


def test_detects_oversized_page():
    page = _page(content_length=3_000_000)

    issues = detect_page_issues(page, headings=(_h1(page),))

    assert IssueType.PAGE_TOO_LARGE in _issue_types(issues)
    oversized = next(
        issue for issue in issues if issue.issue_type == IssueType.PAGE_TOO_LARGE
    )
    assert oversized.severity == IssueSeverity.LOW


def test_detects_noindex_page():
    page = _page(robots_meta="noindex, nofollow")

    issues = detect_page_issues(page, headings=(_h1(page),))

    assert IssueType.NOINDEX_PAGE in _issue_types(issues)
    noindex = next(
        issue for issue in issues if issue.issue_type == IssueType.NOINDEX_PAGE
    )
    assert noindex.severity == IssueSeverity.MEDIUM


def test_indexable_page_within_size_limit_is_clean():
    page = _page(robots_meta="index, follow", content_length=4096)

    issues = detect_page_issues(page, headings=(_h1(page),))

    assert IssueType.NOINDEX_PAGE not in _issue_types(issues)
    assert IssueType.PAGE_TOO_LARGE not in _issue_types(issues)
