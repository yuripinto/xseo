from tests.domain.test_analysis_page_detectors import _id, _page, _url
from xseo.domain.analysis import (
    detect_canonical_target_issues,
    detect_duplicate_meta_description_issues,
    detect_duplicate_title_issues,
)
from xseo.domain.enums import IssueSeverity, IssueType
from xseo.domain.ids import PageId


def test_detects_duplicate_titles_after_case_and_whitespace_normalization():
    first = _page(page_id=_id(PageId, "page-1"), title=" Shared   Title ")
    second = _page(
        page_id=_id(PageId, "page-2"),
        url=_url("https://example.com/two"),
        title="shared title",
    )
    unique = _page(
        page_id=_id(PageId, "page-3"),
        url=_url("https://example.com/three"),
        title="Unique Title",
    )

    issues = detect_duplicate_title_issues((unique, second, first))

    assert [issue.page_id.value for issue in issues] == ["page-1", "page-2"]
    assert {issue.issue_type for issue in issues} == {IssueType.TITLE_DUPLICATE}
    assert {issue.severity for issue in issues} == {IssueSeverity.MEDIUM}


def test_detects_duplicate_meta_descriptions_and_ignores_blank_values():
    first = _page(page_id=_id(PageId, "page-1"), meta_description=" Same description ")
    second = _page(
        page_id=_id(PageId, "page-2"),
        url=_url("https://example.com/two"),
        meta_description="same   DESCRIPTION",
    )
    blank = _page(
        page_id=_id(PageId, "page-3"),
        url=_url("https://example.com/three"),
        meta_description=" ",
    )

    issues = detect_duplicate_meta_description_issues((blank, second, first))

    assert [issue.page_id.value for issue in issues] == ["page-1", "page-2"]
    assert {issue.issue_type for issue in issues} == {
        IssueType.META_DESCRIPTION_DUPLICATE
    }


def test_self_referential_canonical_is_not_flagged():
    page = _page(
        url=_url("https://example.com/a"),
        canonical_url=_url("https://example.com/a"),
    )

    assert detect_canonical_target_issues((page,)) == ()


def test_flags_canonical_pointing_to_noindex_page():
    source = _page(
        page_id=_id(PageId, "page-1"),
        url=_url("https://example.com/a"),
        canonical_url=_url("https://example.com/b"),
    )
    target = _page(
        page_id=_id(PageId, "page-2"),
        url=_url("https://example.com/b"),
        robots_meta="noindex, follow",
    )

    issues = detect_canonical_target_issues((source, target))

    assert [issue.issue_type for issue in issues] == [IssueType.CANONICAL_TO_NOINDEX]
    assert issues[0].severity == IssueSeverity.HIGH
    assert issues[0].page_id == source.page_id


def test_flags_canonical_pointing_to_redirect():
    source = _page(
        page_id=_id(PageId, "page-1"),
        url=_url("https://example.com/a"),
        canonical_url=_url("https://example.com/b"),
    )
    target = _page(
        page_id=_id(PageId, "page-2"),
        url=_url("https://example.com/b"),
        status_code=301,
    )

    issues = detect_canonical_target_issues((source, target))

    assert [issue.issue_type for issue in issues] == [IssueType.CANONICAL_TO_REDIRECT]
    assert issues[0].severity == IssueSeverity.MEDIUM


def test_flags_cross_domain_canonical():
    source = _page(
        url=_url("https://example.com/a"),
        canonical_url=_url("https://other.com/a"),
    )

    issues = detect_canonical_target_issues((source,))

    assert [issue.issue_type for issue in issues] == [IssueType.CANONICAL_CROSS_DOMAIN]
    assert issues[0].severity == IssueSeverity.MEDIUM


def test_canonical_to_healthy_target_is_not_flagged():
    source = _page(
        page_id=_id(PageId, "page-1"),
        url=_url("https://example.com/a"),
        canonical_url=_url("https://example.com/b"),
    )
    target = _page(
        page_id=_id(PageId, "page-2"),
        url=_url("https://example.com/b"),
    )

    assert detect_canonical_target_issues((source, target)) == ()
