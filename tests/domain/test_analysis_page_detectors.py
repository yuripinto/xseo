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
        "has_viewport": True,
        "has_lang": True,
        "has_charset": True,
        "has_open_graph": True,
        "has_structured_data": True,
        "mixed_content_count": 0,
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


def test_flags_pages_deeper_than_max_crawl_depth():
    deep = _page(depth=5)

    issues = detect_page_issues(deep, headings=(_h1(deep),))

    assert IssueType.PAGE_TOO_DEEP in _issue_types(issues)
    too_deep = next(i for i in issues if i.issue_type == IssueType.PAGE_TOO_DEEP)
    assert too_deep.severity == IssueSeverity.LOW
    assert "5 clicks" in too_deep.explanation


def test_page_within_max_crawl_depth_is_not_flagged():
    shallow = _page(depth=2)

    issues = detect_page_issues(shallow, headings=(_h1(shallow),))

    assert IssueType.PAGE_TOO_DEEP not in _issue_types(issues)


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


def test_detects_images_missing_alt():
    page = _page(image_count=5, images_missing_alt=2)

    issues = detect_page_issues(page, headings=(_h1(page),))

    assert IssueType.IMAGES_MISSING_ALT in _issue_types(issues)
    issue = next(i for i in issues if i.issue_type == IssueType.IMAGES_MISSING_ALT)
    assert issue.severity == IssueSeverity.LOW
    assert "2 of 5" in issue.explanation


def test_page_with_all_images_described_is_clean():
    page = _page(image_count=4, images_missing_alt=0)

    issues = detect_page_issues(page, headings=(_h1(page),))

    assert IssueType.IMAGES_MISSING_ALT not in _issue_types(issues)


def test_detects_missing_head_meta():
    page = _page(has_viewport=False, has_lang=False, has_charset=False)

    types = _issue_types(detect_page_issues(page, headings=(_h1(page),)))

    assert IssueType.MISSING_VIEWPORT in types
    assert IssueType.MISSING_LANG in types
    assert IssueType.MISSING_CHARSET in types


def test_missing_viewport_is_medium_severity():
    page = _page(has_viewport=False)

    issues = detect_page_issues(page, headings=(_h1(page),))
    viewport = next(
        issue for issue in issues if issue.issue_type == IssueType.MISSING_VIEWPORT
    )

    assert viewport.severity == IssueSeverity.MEDIUM


def test_page_with_head_meta_present_is_clean():
    page = _page(has_viewport=True, has_lang=True, has_charset=True)

    types = _issue_types(detect_page_issues(page, headings=(_h1(page),)))

    assert IssueType.MISSING_VIEWPORT not in types
    assert IssueType.MISSING_LANG not in types
    assert IssueType.MISSING_CHARSET not in types


def test_detects_mixed_content_as_high_severity():
    page = _page(mixed_content_count=3)

    issues = detect_page_issues(page, headings=(_h1(page),))

    assert IssueType.MIXED_CONTENT in _issue_types(issues)
    mixed = next(i for i in issues if i.issue_type == IssueType.MIXED_CONTENT)
    assert mixed.severity == IssueSeverity.HIGH
    assert "3 resources" in mixed.explanation


def test_no_mixed_content_when_count_zero():
    page = _page(mixed_content_count=0)

    assert IssueType.MIXED_CONTENT not in _issue_types(
        detect_page_issues(page, headings=(_h1(page),))
    )


def test_detects_missing_open_graph_and_structured_data():
    page = _page(has_open_graph=False, has_structured_data=False)

    types = _issue_types(detect_page_issues(page, headings=(_h1(page),)))

    assert IssueType.OPEN_GRAPH_MISSING in types
    assert IssueType.STRUCTURED_DATA_MISSING in types


def test_page_with_social_and_structured_data_is_clean():
    page = _page(has_open_graph=True, has_structured_data=True)

    types = _issue_types(detect_page_issues(page, headings=(_h1(page),)))

    assert IssueType.OPEN_GRAPH_MISSING not in types
    assert IssueType.STRUCTURED_DATA_MISSING not in types


def test_detects_hreflang_without_self_reference():
    page = _page(has_hreflang=True, hreflang_self_referential=False)

    issues = detect_page_issues(page, headings=(_h1(page),))

    assert IssueType.HREFLANG_NO_SELF_REFERENCE in _issue_types(issues)
    hreflang = next(
        i for i in issues if i.issue_type == IssueType.HREFLANG_NO_SELF_REFERENCE
    )
    assert hreflang.severity == IssueSeverity.MEDIUM


def test_self_referential_hreflang_is_clean():
    page = _page(has_hreflang=True, hreflang_self_referential=True)

    assert IssueType.HREFLANG_NO_SELF_REFERENCE not in _issue_types(
        detect_page_issues(page, headings=(_h1(page),))
    )


def test_page_without_hreflang_is_not_flagged():
    # A page that uses no hreflang at all must never be flagged, even though
    # "self_referential" is vacuously false-ish for an empty set.
    page = _page(has_hreflang=False, hreflang_self_referential=False)

    assert IssueType.HREFLANG_NO_SELF_REFERENCE not in _issue_types(
        detect_page_issues(page, headings=(_h1(page),))
    )
