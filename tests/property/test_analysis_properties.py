from hypothesis import given
from hypothesis import strategies as st

from tests.strategies.domain import content_hashes, crawl_ids
from tests.domain.test_analysis_page_detectors import _id, _page, _url
from xseo.domain.analysis import IssueAnalysisService, LinkStatusRecord, detect_page_issues
from xseo.domain.duplicates import detect_duplicate_groups
from xseo.domain.entities import Heading
from xseo.domain.enums import HeadingLevel, IssueType, LinkRelation
from xseo.domain.ids import PageId
from xseo.domain.value_objects import WordCount


@given(st.integers(min_value=0, max_value=80))
def test_title_threshold_classification_is_deterministic(title_length):
    title = "T" * title_length
    page = _page(title=title, word_count=WordCount.create(250).value)
    headings = (Heading(page.page_id, HeadingLevel.H1, "Heading", 1),)

    first = detect_page_issues(page, headings)
    second = detect_page_issues(page, headings)

    assert [issue.issue_id.value for issue in first] == [issue.issue_id.value for issue in second]
    issue_types = {issue.issue_type for issue in first}
    if title_length == 0:
        assert IssueType.TITLE_MISSING in issue_types
    elif title_length < 30:
        assert IssueType.TITLE_TOO_SHORT in issue_types
    elif title_length > 60:
        assert IssueType.TITLE_TOO_LONG in issue_types
    else:
        assert not issue_types.intersection(
            {IssueType.TITLE_MISSING, IssueType.TITLE_TOO_SHORT, IssueType.TITLE_TOO_LONG}
        )


@given(
    crawl_ids(),
    content_hashes(),
    st.lists(st.integers(min_value=1, max_value=1000), min_size=2, max_size=8, unique=True),
)
def test_duplicate_groups_are_deterministic_and_only_include_duplicate_hash_pages(generated_crawl_id, content_hash, suffixes):
    crawl_id = generated_crawl_id
    pages = tuple(
        _page(
            crawl_id=crawl_id,
            page_id=_id(PageId, f"page-{suffix}"),
            url=_url(f"https://example.com/{suffix}"),
            content_hash=content_hash,
        )
        for suffix in suffixes
    )

    first = detect_duplicate_groups(crawl_id, tuple(reversed(pages)))
    second = detect_duplicate_groups(crawl_id, pages)

    assert len(first) == 1
    assert [page_id.value for page_id in first[0].page_ids] == sorted(
        page.page_id.value for page in pages
    )
    assert first == second


@given(crawl_ids())
def test_issue_service_suppresses_duplicate_issue_records(generated_crawl_id):
    crawl_id = generated_crawl_id
    page = _page(crawl_id=crawl_id)
    heading = Heading(page.page_id, HeadingLevel.H1, "Heading", 1)
    target = _url("https://example.com/missing")
    duplicate_record = LinkStatusRecord(
        page.page_id,
        page.final_url,
        target,
        LinkRelation.INTERNAL,
        404,
    )

    issues = IssueAnalysisService().detect_issues(
        crawl_id,
        (page,),
        headings=(heading,),
        link_statuses=(duplicate_record, duplicate_record),
    )

    issue_ids = [issue.issue_id.value for issue in issues]
    assert len(issue_ids) == len(set(issue_ids))
