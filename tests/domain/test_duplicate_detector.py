from tests.domain.test_analysis_page_detectors import _id, _page, _url
from xseo.domain.duplicates import detect_duplicate_groups
from xseo.domain.ids import CrawlId, PageId
from xseo.domain.value_objects import ContentHash


def test_detects_exact_duplicate_groups_by_content_hash():
    crawl_id = _id(CrawlId, "crawl-1")
    shared_hash = ContentHash.create("hash-shared").value
    pages = (
        _page(
            crawl_id=crawl_id,
            page_id=_id(PageId, "page-3"),
            url=_url("https://example.com/three"),
            content_hash=shared_hash,
        ),
        _page(
            crawl_id=crawl_id,
            page_id=_id(PageId, "page-1"),
            url=_url("https://example.com/one"),
            content_hash=shared_hash,
        ),
        _page(
            crawl_id=crawl_id,
            page_id=_id(PageId, "page-2"),
            url=_url("https://example.com/two"),
            content_hash=ContentHash.create("hash-unique").value,
        ),
    )

    groups = detect_duplicate_groups(crawl_id, pages)

    assert len(groups) == 1
    assert groups[0].content_hash == shared_hash
    assert [page_id.value for page_id in groups[0].page_ids] == ["page-1", "page-3"]


def test_ignores_singleton_and_missing_content_hashes():
    crawl_id = _id(CrawlId, "crawl-1")
    pages = (
        _page(crawl_id=crawl_id, page_id=_id(PageId, "page-1"), content_hash=None),
        _page(
            crawl_id=crawl_id,
            page_id=_id(PageId, "page-2"),
            url=_url("https://example.com/two"),
            content_hash=ContentHash.create("hash-unique").value,
        ),
    )

    assert detect_duplicate_groups(crawl_id, pages) == ()
