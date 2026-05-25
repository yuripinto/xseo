from tests.domain.test_analysis_page_detectors import _id, _page, _url
from xseo.domain.analysis import (
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
