from datetime import UTC, datetime

from xseo.application import StartCrawlCommand, StopCrawlCommand
from xseo.application.services import ActiveCrawlRegistry, CrawlApplicationService, EventDeliveryService
from xseo.domain.ids import CrawlId


class Clock:
    def now(self):
        return datetime(2026, 1, 1, tzinfo=UTC)


class CrawlRepository:
    def __init__(self):
        self.crawls = {}

    def save_crawl(self, crawl):
        self.crawls[crawl.crawl_id.value] = crawl
        return crawl.crawl_id

    def get_crawl(self, crawl_id):
        return self.crawls.get(crawl_id.value)


class BackgroundExecution:
    def __init__(self):
        self.started = []
        self.stop_requests = []

    def start(self, crawl_id, work):
        self.started.append((crawl_id, work))
        return object()

    def request_stop(self, crawl_id):
        self.stop_requests.append(crawl_id)


def _crawl_id():
    return CrawlId.create("crawl-service").value


def test_start_crawl_validates_and_delegates_to_background_execution():
    repository = CrawlRepository()
    background = BackgroundExecution()
    events = EventDeliveryService()
    delivered = []
    crawl_id = _crawl_id()
    events.subscribe(crawl_id, lambda event: delivered.append(event))
    service = CrawlApplicationService(
        repository,
        background,
        ActiveCrawlRegistry(),
        event_delivery=events,
        clock=Clock(),
        crawl_id_factory=lambda: crawl_id,
    )

    result = service.start_crawl(StartCrawlCommand("https://example.com/"))

    assert result.success
    assert result.value.crawl_id == crawl_id
    assert len(background.started) == 1
    assert repository.get_crawl(crawl_id) is not None
    assert len(delivered) == 1


def test_start_crawl_rejects_invalid_url():
    service = CrawlApplicationService(CrawlRepository(), BackgroundExecution(), ActiveCrawlRegistry(), clock=Clock())

    result = service.start_crawl(StartCrawlCommand("ftp://example.com/"))

    assert not result.success
    assert result.error_code == "crawl.invalid_start_url"


def test_stop_crawl_delegates_to_active_registry_and_background():
    background = BackgroundExecution()
    registry = ActiveCrawlRegistry()
    crawl_id = _crawl_id()
    registry.register(crawl_id, object())
    service = CrawlApplicationService(CrawlRepository(), background, registry, clock=Clock())

    result = service.request_stop(StopCrawlCommand(crawl_id))

    assert result.success
    assert background.stop_requests == [crawl_id]
