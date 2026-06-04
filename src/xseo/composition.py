"""Headless composition root.

Wires every adapter and application service into a ready-to-use object graph,
without importing the UI toolkit. Both the desktop app (``xseo.ui.app``) and the
command-line interface (``xseo.cli``) build on top of this, and a future hosted
backend can reuse the exact same graph.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from xseo.adapters.background import ThreadedBackgroundExecution
from xseo.adapters.crawl_processor import PageProcessorLinkDiscovery
from xseo.adapters.event_bridge import DomainToAppEventBridge
from xseo.adapters.export import CsvExportAdapter
from xseo.adapters.http import (
    AllowAllRobotsPolicy,
    RobotsTxtPolicy,
    SyncHttpFetchAdapter,
    httpx_robots_fetcher,
)
from xseo.adapters.persistence import (
    SQLiteAnalysisRepository,
    SQLiteCrawlDataRepository,
    SQLiteCrawlRepository,
    SQLiteDatabase,
    SQLiteExportRepository,
    SQLiteResultsReadRepository,
)
from xseo.adapters.sitemap import HttpSitemapAuditor
from xseo.application.services import (
    ExportApplicationService,
    ResultsApplicationService,
)
from xseo.application.services.active_crawls import ActiveCrawlRegistry
from xseo.application.services.crawl_execution import CrawlExecutionCoordinator
from xseo.application.services.crawl_service import CrawlApplicationService
from xseo.application.services.event_delivery import EventDeliveryService
from xseo.domain.analysis import IssueAnalysisService
from xseo.domain.crawler import UrlCrawlEngine
from xseo.domain.duplicates import detect_duplicate_groups
from xseo.domain.extraction.pipeline import SeoExtractionPipeline
from xseo.ui.desktop import XseoDesktopController

DEFAULT_DB = Path.home() / ".xseo" / "xseo.sqlite3"


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


@dataclass(frozen=True)
class Services:
    """The wired object graph shared by every front end.

    Iterable as ``(controller, results_service, event_delivery)`` for backward
    compatibility with existing call sites; ``bg_execution`` is exposed so a
    headless caller can join the background crawl thread.
    """

    controller: XseoDesktopController
    results_service: ResultsApplicationService
    event_delivery: EventDeliveryService
    bg_execution: ThreadedBackgroundExecution

    def __iter__(self):
        return iter((self.controller, self.results_service, self.event_delivery))


def build_services(db_path: Path | str = DEFAULT_DB) -> Services:
    """Wire all adapters and services against the SQLite database at ``db_path``."""
    db = SQLiteDatabase(str(db_path)).initialize()
    conn = db.connect()

    crawl_repo = SQLiteCrawlRepository(conn)
    data_repo = SQLiteCrawlDataRepository(conn)
    analysis_repo = SQLiteAnalysisRepository(conn)
    read_repo = SQLiteResultsReadRepository(conn)
    export_repo = SQLiteExportRepository(conn)

    csv_adapter = CsvExportAdapter()
    export_svc = ExportApplicationService(read_repo, csv_adapter, export_repo)
    event_delivery = EventDeliveryService()
    active_crawls = ActiveCrawlRegistry()
    bg_execution = ThreadedBackgroundExecution()
    clock = SystemClock()

    def work_factory(crawl: object) -> object:
        bridge = DomainToAppEventBridge(event_delivery, crawl.crawl_id, clock)
        processor = PageProcessorLinkDiscovery(
            SeoExtractionPipeline(), data_repo, crawl.crawl_id
        )
        if crawl.config.respect_robots:
            robots_policy = RobotsTxtPolicy(
                httpx_robots_fetcher(crawl.config.timeout_seconds)
            )
        else:
            robots_policy = AllowAllRobotsPolicy()
        engine = UrlCrawlEngine(
            fetch_port=SyncHttpFetchAdapter(),
            event_publisher=bridge,
            clock=clock,
            link_discovery=processor,
            robots_policy=robots_policy,
            request_delay_seconds=crawl.config.request_delay_seconds,
        )
        sitemap_auditor = HttpSitemapAuditor(
            httpx_robots_fetcher(crawl.config.timeout_seconds)
        )
        coordinator = CrawlExecutionCoordinator(
            crawl_engine=engine,
            issue_analysis_service=IssueAnalysisService(),
            duplicate_detector=detect_duplicate_groups,
            crawl_data_repository=data_repo,
            analysis_repository=analysis_repo,
            event_delivery=event_delivery,
            clock=clock,
            sitemap_auditor=sitemap_auditor,
        )

        def work(stop_token: object) -> object:
            return coordinator.run(crawl, stop_token=stop_token)

        return work

    crawl_svc = CrawlApplicationService(
        crawl_repo,
        bg_execution,
        active_crawls,
        event_delivery,
        clock,
        work_factory=work_factory,
    )
    results_svc = ResultsApplicationService(read_repo)
    controller = XseoDesktopController(crawl_svc, results_svc, export_svc)

    return Services(controller, results_svc, event_delivery, bg_execution)
