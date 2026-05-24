from datetime import UTC, datetime

from xseo.domain.entities import CrawlConfig
from xseo.domain.events import CrawlStarted
from xseo.domain.ids import CrawlId
from xseo.domain.urls import BaseUrl


def test_crawl_started_event_has_required_payload():
    crawl_id = CrawlId.create("crawl-1").value
    base_url = BaseUrl.create("https://example.com").value
    config = CrawlConfig.create(base_url).value
    occurred_at = datetime(2026, 1, 1, tzinfo=UTC)

    event = CrawlStarted(crawl_id=crawl_id, occurred_at=occurred_at, config=config)

    assert event.crawl_id == crawl_id
    assert event.occurred_at == occurred_at
    assert event.config == config
