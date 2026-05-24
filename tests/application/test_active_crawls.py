from xseo.application.services import ActiveCrawlRegistry
from xseo.domain.ids import CrawlId


class StopHandle:
    def __init__(self):
        self.stop_count = 0

    def request_stop(self):
        self.stop_count += 1


def _crawl_id():
    return CrawlId.create("crawl-1").value


def test_stop_request_is_idempotent():
    registry = ActiveCrawlRegistry()
    handle = StopHandle()
    crawl_id = _crawl_id()
    registry.register(crawl_id, handle)

    first = registry.request_stop(crawl_id)
    second = registry.request_stop(crawl_id)

    assert first.success
    assert second.success
    assert handle.stop_count == 1
    assert first.value.stop_requested
    assert second.value.stop_requested


def test_missing_active_crawl_returns_failure_result():
    result = ActiveCrawlRegistry().request_stop(_crawl_id())

    assert not result.success
    assert result.error_code == "crawl.not_active"
