"""Crawl application service."""

from __future__ import annotations

from datetime import UTC, datetime

from xseo.application.events import CrawlProgressEvent, CrawlProgressEventKind
from xseo.application.read_models import CrawlProgressStatus, CrawlSession
from xseo.application.results import ApplicationResult
from xseo.domain.entities import Crawl, CrawlConfig
from xseo.domain.ids import CrawlId
from xseo.domain.urls import BaseUrl


class CrawlApplicationService:
    def __init__(
        self,
        crawl_repository,
        background_execution,
        active_crawls,
        event_delivery=None,
        clock=None,
        crawl_id_factory=None,
        work_factory=None,
    ):
        self.crawl_repository = crawl_repository
        self.background_execution = background_execution
        self.active_crawls = active_crawls
        self.event_delivery = event_delivery
        self.clock = clock or _SystemClock()
        self.crawl_id_factory = crawl_id_factory or _default_crawl_id
        self.work_factory = work_factory

    def start_crawl(self, command):
        start_url = BaseUrl.create(command.start_url)
        if not start_url.ok:
            return ApplicationResult.fail(
                "Start URL is invalid", "crawl.invalid_start_url"
            )
        config = CrawlConfig.create(
            start_url.value,
            same_host_only=command.same_host_only,
            page_limit=command.page_limit,
            timeout_seconds=command.timeout_seconds,
            request_delay_seconds=command.request_delay_seconds,
            respect_robots=command.respect_robots,
        )
        if not config.ok:
            return ApplicationResult.fail(
                config.first_error.message, str(config.first_error.code)
            )

        crawl_id = self.crawl_id_factory()
        crawl = Crawl.create(crawl_id, config.value, self.clock.now())
        self.crawl_repository.save_crawl(crawl)
        work = (
            self.work_factory(crawl) if self.work_factory is not None else lambda: None
        )
        control_handle = self.background_execution.start(crawl_id, work)
        registered = self.active_crawls.register(crawl_id, control_handle, crawl.status)
        if not registered.success:
            return registered
        session = CrawlSession(crawl_id, crawl.status, created_at=crawl.created_at)
        self._publish(
            crawl_id,
            CrawlProgressEventKind.CRAWL_STARTED,
            session.status,
            "Crawl started",
        )
        return ApplicationResult.ok(session)

    def request_stop(self, command):
        result = self.active_crawls.request_stop(command.crawl_id)
        if not result.success:
            return result
        if hasattr(self.background_execution, "request_stop"):
            self.background_execution.request_stop(command.crawl_id)
        self._publish(
            command.crawl_id,
            CrawlProgressEventKind.STATUS_CHANGED,
            result.value.status,
            "Stop requested",
        )
        return result

    def get_status(self, crawl_id):
        crawl = self.crawl_repository.get_crawl(crawl_id)
        if crawl is None:
            return ApplicationResult.fail("Crawl was not found", "crawl.not_found")
        return ApplicationResult.ok(
            CrawlProgressStatus(
                crawl_id=crawl.crawl_id,
                status=crawl.status,
                created_at=crawl.created_at,
                started_at=crawl.started_at,
                completed_at=crawl.completed_at,
            )
        )

    def _publish(self, crawl_id, kind, status, message):
        if self.event_delivery is None:
            return
        self.event_delivery.publish(
            CrawlProgressEvent(crawl_id, kind, status, self.clock.now(), message)
        )


class _SystemClock:
    def now(self):
        return datetime.now(UTC)


def _default_crawl_id():
    return CrawlId.create(f"crawl-{datetime.now(UTC).isoformat()}").value
