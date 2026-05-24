"""Adapter-neutral crawl execution coordinator."""

from __future__ import annotations

from xseo.application.events import CrawlProgressEvent, CrawlProgressEventKind
from xseo.application.results import ApplicationResult
from xseo.domain.enums import CrawlStatus


class CrawlExecutionCoordinator:
    def __init__(
        self,
        crawl_engine=None,
        issue_analysis_service=None,
        duplicate_detector=None,
        crawl_data_repository=None,
        analysis_repository=None,
        event_delivery=None,
        clock=None,
    ):
        self.crawl_engine = crawl_engine
        self.issue_analysis_service = issue_analysis_service
        self.duplicate_detector = duplicate_detector
        self.crawl_data_repository = crawl_data_repository
        self.analysis_repository = analysis_repository
        self.event_delivery = event_delivery
        self.clock = clock

    def run(self, crawl, stop_token=None):
        if self.crawl_engine is None:
            return ApplicationResult.fail("Crawl engine is not configured", "crawl.engine_missing")
        try:
            result = self.crawl_engine.run(crawl, stop_token=stop_token)
        except Exception as exc:
            self._publish_failure(crawl.crawl_id, exc)
            return ApplicationResult.fail(str(exc), "crawl.execution_failed")
        try:
            self._run_analysis(result.crawl.crawl_id)
        except Exception as exc:
            self._publish_failure(result.crawl.crawl_id, exc)
            return ApplicationResult.fail(str(exc), "crawl.analysis_failed")
        self._publish_terminal(result.crawl.crawl_id, result.final_status)
        return ApplicationResult.ok(result)

    def _run_analysis(self, crawl_id):
        if self.crawl_data_repository is None or self.analysis_repository is None:
            return
        data = self.crawl_data_repository.load_analysis_data(crawl_id)
        pages = getattr(data, "pages", ())
        headings = getattr(data, "headings", ())
        link_statuses = getattr(data, "link_statuses", ())
        if self.issue_analysis_service is not None:
            issues = self.issue_analysis_service.detect_issues(crawl_id, pages, headings, link_statuses)
            self.analysis_repository.save_issues(crawl_id, issues)
        if self.duplicate_detector is not None:
            groups = self.duplicate_detector(crawl_id, pages)
            self.analysis_repository.save_duplicate_groups(crawl_id, groups)

    def _publish_terminal(self, crawl_id, status):
        if self.event_delivery is None or self.clock is None:
            return
        self.event_delivery.publish(
            CrawlProgressEvent(
                crawl_id,
                CrawlProgressEventKind.STATUS_CHANGED,
                status,
                self.clock.now(),
                "Crawl execution finished",
            )
        )

    def _publish_failure(self, crawl_id, exc):
        if self.event_delivery is None or self.clock is None:
            return
        self.event_delivery.publish(
            CrawlProgressEvent(
                crawl_id,
                CrawlProgressEventKind.CRAWL_FAILED,
                CrawlStatus.FAILED,
                self.clock.now(),
                f"Crawl execution failed: {exc}",
            )
        )
