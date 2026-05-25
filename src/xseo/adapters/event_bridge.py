"""Bridge: converts domain events to application CrawlProgressEvent."""

from __future__ import annotations

from xseo.application.events import CrawlProgressEvent, CrawlProgressEventKind
from xseo.domain.enums import CrawlStatus, FetchStatus
from xseo.domain.events import (
    CrawlCompleted,
    CrawlFailed,
    CrawlProgressed,
    CrawlStarted,
    CrawlStopped,
    PageFetched,
)


class DomainToAppEventBridge:
    """Satisfies the domain EventPublisherPort; forwards translated events to EventDeliveryService."""

    def __init__(self, event_delivery: object, crawl_id: object, clock: object) -> None:
        self.event_delivery = event_delivery
        self.crawl_id = crawl_id
        self.clock = clock
        self._pages_crawled: int = 0
        self._errors: int = 0

    def publish(self, event: object) -> None:
        kind, status, message = self._translate(event)
        if kind is None:
            return
        self.event_delivery.publish(
            CrawlProgressEvent(self.crawl_id, kind, status, self.clock.now(), message)
        )

    def _translate(
        self, event: object
    ) -> tuple[CrawlProgressEventKind | None, object, str | None]:
        if isinstance(event, CrawlStarted):
            return (
                CrawlProgressEventKind.CRAWL_STARTED,
                CrawlStatus.RUNNING,
                "Crawl started",
            )

        if isinstance(event, PageFetched):
            if event.status == FetchStatus.SUCCESS:
                self._pages_crawled += 1
            else:
                self._errors += 1
            url_str = getattr(event.url, "value", str(event.url))
            msg = f"Fetched {url_str} ({self._pages_crawled} pages, {self._errors} errors)"
            return CrawlProgressEventKind.PAGE_FETCHED, CrawlStatus.RUNNING, msg

        if isinstance(event, CrawlProgressed):
            msg = f"{event.pages_crawled} pages crawled, {event.queued_count} queued"
            return CrawlProgressEventKind.PAGE_FETCHED, CrawlStatus.RUNNING, msg

        if isinstance(event, CrawlCompleted):
            return (
                CrawlProgressEventKind.CRAWL_COMPLETED,
                CrawlStatus.COMPLETED,
                f"Completed: {event.pages_crawled} pages",
            )

        if isinstance(event, CrawlStopped):
            return (
                CrawlProgressEventKind.CRAWL_STOPPED,
                CrawlStatus.STOPPED,
                f"Stopped: {event.pages_crawled} pages",
            )

        if isinstance(event, CrawlFailed):
            return (
                CrawlProgressEventKind.CRAWL_FAILED,
                CrawlStatus.FAILED,
                f"Failed: {event.error.message}",
            )

        return None, None, None
