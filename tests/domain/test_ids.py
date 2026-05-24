from xseo.domain.ids import CrawlId, PageId


def test_typed_id_rejects_empty_value():
    result = CrawlId.create("")

    assert not result.ok
    assert result.errors


def test_different_id_types_are_not_equal():
    crawl_id = CrawlId.create("same").value
    page_id = PageId.create("same").value

    assert crawl_id != page_id
