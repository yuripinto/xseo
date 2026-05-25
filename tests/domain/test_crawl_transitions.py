from datetime import UTC, datetime

from xseo.domain.entities import Crawl, CrawlConfig
from xseo.domain.enums import CrawlStatus
from xseo.domain.errors import DomainError
from xseo.domain.ids import CrawlId
from xseo.domain.urls import BaseUrl


def _crawl():
    crawl_id = CrawlId.create("crawl-1").value
    base_url = BaseUrl.create("https://example.com").value
    config = CrawlConfig.create(base_url).value
    return Crawl.create(crawl_id, config, datetime(2026, 1, 1, tzinfo=UTC))


def test_crawl_start_returns_new_running_instance():
    crawl = _crawl()

    result = crawl.start(datetime(2026, 1, 1, 0, 1, tzinfo=UTC))

    assert result.ok
    assert crawl.status == CrawlStatus.CREATED
    assert result.value.status == CrawlStatus.RUNNING


def test_invalid_transition_returns_validation_failure():
    crawl = _crawl()

    result = crawl.complete(datetime(2026, 1, 1, tzinfo=UTC))

    assert not result.ok


def test_running_crawl_can_fail():
    crawl = _crawl().start(datetime(2026, 1, 1, tzinfo=UTC)).value

    result = crawl.fail(
        DomainError.of("x", "failed"), datetime(2026, 1, 1, 0, 2, tzinfo=UTC)
    )

    assert result.ok
    assert result.value.status == CrawlStatus.FAILED
