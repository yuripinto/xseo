from datetime import UTC, datetime, timedelta

from xseo.domain.crawler import UrlCrawlEngine
from xseo.domain.entities import Crawl, CrawlConfig, FetchResult
from xseo.domain.enums import CrawlStatus, FetchStatus
from xseo.domain.errors import DomainError
from xseo.domain.events import CrawlFailed
from xseo.domain.ids import CrawlId
from xseo.domain.urls import BaseUrl, NormalizedUrl


class FakeClock:
    def __init__(self):
        self.current = datetime(2026, 1, 1, tzinfo=UTC)

    def now(self):
        self.current += timedelta(seconds=1)
        return self.current


class FakePublisher:
    def __init__(self, fail_on_call=None):
        self.events = []
        self.fail_on_call = fail_on_call
        self.failed = False

    def publish(self, event):
        if not self.failed and self.fail_on_call == len(self.events) + 1:
            self.failed = True
            raise RuntimeError("publish failed")
        self.events.append(event)


class FakeFetch:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.requested = []

    def fetch(self, url):
        self.requested.append(url)
        if self.outcomes:
            return self.outcomes.pop(0)
        return FetchResult(
            url, url, FetchStatus.SUCCESS, status_code=200, content_type="text/html"
        )


class FakeDiscovery:
    def __init__(self, links):
        self.links = tuple(links)

    def discover_links(self, fetch_result):
        return self.links


class FakeRobots:
    def __init__(self, disallowed):
        self.disallowed = set(disallowed)

    def is_allowed(self, url):
        return getattr(url, "value", url) not in self.disallowed


class StopAfterChecks:
    def __init__(self, stop_at):
        self.stop_at = stop_at
        self.checks = 0

    def is_stop_requested(self):
        self.checks += 1
        return self.checks >= self.stop_at


def _crawl(limit=2):
    crawl_id = CrawlId.create("crawl-1").value
    base_url = BaseUrl.create("https://example.com/").value
    config = CrawlConfig.create(base_url, page_limit=limit).value
    return Crawl.create(crawl_id, config, datetime(2026, 1, 1, tzinfo=UTC))


def _fetch_result(url="https://example.com/"):
    normalized = NormalizedUrl.create(url).value
    return FetchResult(
        requested_url=normalized,
        final_url=normalized,
        status=FetchStatus.SUCCESS,
        status_code=200,
        content_type="text/html",
    )


def test_crawl_engine_stops_at_successful_page_limit():
    fetch = FakeFetch(
        [_fetch_result("https://example.com/"), _fetch_result("https://example.com/a")]
    )
    engine = UrlCrawlEngine(
        fetch,
        FakePublisher(),
        FakeClock(),
        link_discovery=FakeDiscovery(["/a", "/b"]),
    )

    result = engine.run(_crawl(limit=2))

    assert result.final_status == CrawlStatus.COMPLETED
    assert result.successful_page_count == 2
    assert len(fetch.requested) == 2


def test_stop_before_fetch_prevents_fetch():
    fetch = FakeFetch([])
    engine = UrlCrawlEngine(fetch, FakePublisher(), FakeClock())

    result = engine.run(_crawl(), stop_token=StopAfterChecks(stop_at=1))

    assert result.final_status == CrawlStatus.STOPPED
    assert fetch.requested == []


def test_event_publication_failure_fails_crawl():
    publisher = FakePublisher(fail_on_call=1)
    engine = UrlCrawlEngine(FakeFetch([]), publisher, FakeClock())

    result = engine.run(_crawl())

    assert result.final_status == CrawlStatus.FAILED
    assert result.failure == DomainError.of("event.publish_failed", "publish failed")


def test_crawl_engine_publishes_failed_event_when_progress_publish_fails():
    publisher = FakePublisher(fail_on_call=4)
    engine = UrlCrawlEngine(FakeFetch([_fetch_result()]), publisher, FakeClock())

    result = engine.run(_crawl())

    assert result.final_status == CrawlStatus.FAILED
    assert isinstance(publisher.events[-1], CrawlFailed)


def test_robots_disallows_start_url_skips_all_fetching():
    fetch = FakeFetch([])
    robots = FakeRobots(disallowed={"https://example.com/"})
    engine = UrlCrawlEngine(fetch, FakePublisher(), FakeClock(), robots_policy=robots)

    result = engine.run(_crawl())

    assert result.final_status == CrawlStatus.COMPLETED
    assert result.successful_page_count == 0
    assert fetch.requested == []


def test_robots_disallows_discovered_link():
    fetch = FakeFetch(
        [_fetch_result("https://example.com/"), _fetch_result("https://example.com/b")]
    )
    robots = FakeRobots(disallowed={"https://example.com/a"})
    engine = UrlCrawlEngine(
        fetch,
        FakePublisher(),
        FakeClock(),
        link_discovery=FakeDiscovery(["/a", "/b"]),
        robots_policy=robots,
    )

    engine.run(_crawl(limit=10))

    requested = [url.value for url in fetch.requested]
    assert "https://example.com/a" not in requested
    assert "https://example.com/b" in requested


def test_request_delay_sleeps_between_fetches():
    sleeps = []
    fetch = FakeFetch(
        [_fetch_result("https://example.com/"), _fetch_result("https://example.com/a")]
    )
    engine = UrlCrawlEngine(
        fetch,
        FakePublisher(),
        FakeClock(),
        link_discovery=FakeDiscovery(["/a"]),
        request_delay_seconds=0.25,
        sleeper=sleeps.append,
    )

    engine.run(_crawl(limit=2))

    assert sleeps == [0.25]
