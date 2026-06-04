from datetime import UTC, datetime

from hypothesis import given
from hypothesis import strategies as st

from xseo.domain.crawler import UrlCrawlEngine
from xseo.domain.entities import Crawl, CrawlConfig, FetchResult
from xseo.domain.enums import CrawlStatus, FetchStatus
from xseo.domain.ids import CrawlId
from xseo.domain.urls import BaseUrl


class StaticClock:
    def now(self):
        return datetime(2026, 1, 1, tzinfo=UTC)


class RecordingPublisher:
    def __init__(self):
        self.events = []

    def publish(self, event):
        self.events.append(event)


class SequenceFetch:
    def __init__(self, statuses):
        self.statuses = list(statuses)
        self.requested = []

    def fetch(self, url):
        self.requested.append(url)
        status = self.statuses.pop(0) if self.statuses else FetchStatus.SUCCESS
        return FetchResult(
            requested_url=url,
            final_url=url if status == FetchStatus.SUCCESS else None,
            status=status,
            status_code=200 if status == FetchStatus.SUCCESS else None,
            content_type="text/html" if status == FetchStatus.SUCCESS else None,
        )


class StopAfterFetch:
    def __init__(self, stop_after_fetch_count, fetch):
        self.stop_after_fetch_count = stop_after_fetch_count
        self.fetch = fetch

    def is_stop_requested(self):
        return len(self.fetch.requested) >= self.stop_after_fetch_count


class ManyLinks:
    def discover_links(self, fetch_result, depth=0):
        return tuple(f"/page-{index}" for index in range(20))


def _crawl(limit):
    crawl_id = CrawlId.create("crawl-property").value
    base_url = BaseUrl.create("https://example.com/").value
    config = CrawlConfig.create(base_url, page_limit=limit).value
    return Crawl.create(crawl_id, config, datetime(2026, 1, 1, tzinfo=UTC))


@given(
    st.integers(min_value=1, max_value=10),
    st.lists(st.sampled_from(list(FetchStatus)), min_size=1, max_size=20),
)
def test_crawl_engine_never_exceeds_successful_page_limit(limit, statuses):
    fetch = SequenceFetch(statuses)
    engine = UrlCrawlEngine(
        fetch, RecordingPublisher(), StaticClock(), link_discovery=ManyLinks()
    )

    result = engine.run(_crawl(limit))

    assert result.successful_page_count <= limit


@given(st.integers(min_value=0, max_value=5))
def test_crawl_engine_starts_no_fetch_after_observed_stop(stop_after):
    fetch = SequenceFetch([FetchStatus.SUCCESS] * 10)
    engine = UrlCrawlEngine(
        fetch, RecordingPublisher(), StaticClock(), link_discovery=ManyLinks()
    )

    result = engine.run(_crawl(10), stop_token=StopAfterFetch(stop_after, fetch))

    assert len(fetch.requested) <= max(stop_after, 0)
    if stop_after == 0:
        assert result.final_status == CrawlStatus.STOPPED
