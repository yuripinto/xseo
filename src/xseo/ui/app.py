"""PySide6 desktop application: entry point, DI wiring, and main window."""

from __future__ import annotations

import sys
import traceback
from datetime import UTC, datetime
from pathlib import Path

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QStatusBar,
    QTabWidget,
    QWidget,
)

from xseo.adapters.crawl_processor import PageProcessorLinkDiscovery
from xseo.adapters.event_bridge import DomainToAppEventBridge
from xseo.adapters.export import CsvExportAdapter
from xseo.adapters.http import SyncHttpFetchAdapter
from xseo.adapters.persistence import (
    SQLiteAnalysisRepository,
    SQLiteCrawlDataRepository,
    SQLiteCrawlRepository,
    SQLiteDatabase,
    SQLiteExportRepository,
    SQLiteResultsReadRepository,
)
from xseo.application.commands import PageDetailQuery
from xseo.application.events import CrawlProgressEvent, CrawlProgressEventKind
from xseo.application.services import (
    ExportApplicationService,
    ResultsApplicationService,
)
from xseo.application.services.active_crawls import ActiveCrawlRegistry
from xseo.application.services.crawl_execution import CrawlExecutionCoordinator
from xseo.application.services.crawl_service import CrawlApplicationService
from xseo.application.services.event_delivery import EventDeliveryService
from xseo.adapters.background import ThreadedBackgroundExecution
from xseo.domain.analysis import IssueAnalysisService
from xseo.domain.crawler import UrlCrawlEngine
from xseo.domain.duplicates import detect_duplicate_groups
from xseo.domain.extraction.pipeline import SeoExtractionPipeline
from xseo.ui.bridge import EventBridge
from xseo.ui.desktop import XseoDesktopController
from xseo.ui.widgets.control_panel import ControlPanel
from xseo.ui.widgets.duplicates_tab import DuplicatesTab
from xseo.ui.widgets.issues_tab import IssuesTab
from xseo.ui.widgets.page_detail import PageDetailDialog
from xseo.ui.widgets.pages_tab import PagesTab
from xseo.ui.widgets.progress_tab import ProgressTab

_DEFAULT_DB = Path.home() / ".xseo" / "xseo.sqlite3"


class _SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


def build_services(
    db_path: Path | str = _DEFAULT_DB,
) -> tuple[XseoDesktopController, ResultsApplicationService, EventDeliveryService]:
    """Wire all adapters and services. Returns (controller, results_service, event_delivery)."""
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
    clock = _SystemClock()

    def work_factory(crawl: object) -> object:
        bridge = DomainToAppEventBridge(event_delivery, crawl.crawl_id, clock)
        processor = PageProcessorLinkDiscovery(
            SeoExtractionPipeline(), data_repo, crawl.crawl_id
        )
        engine = UrlCrawlEngine(
            fetch_port=SyncHttpFetchAdapter(),
            event_publisher=bridge,
            clock=clock,
            link_discovery=processor,
        )
        coordinator = CrawlExecutionCoordinator(
            crawl_engine=engine,
            issue_analysis_service=IssueAnalysisService(),
            duplicate_detector=detect_duplicate_groups,
            crawl_data_repository=data_repo,
            analysis_repository=analysis_repo,
            event_delivery=event_delivery,
            clock=clock,
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

    return controller, results_svc, event_delivery


class MainWindow(QMainWindow):
    def __init__(
        self,
        controller: XseoDesktopController,
        results_service: ResultsApplicationService,
        event_delivery: EventDeliveryService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._controller = controller
        self._results_service = results_service
        self._event_delivery = event_delivery
        self._subscription_id: str | None = None

        self.setWindowTitle("xSEO — Local SEO Crawler")
        self.resize(1100, 700)
        self._build_ui()
        self._restore_recent_crawl()

    def _build_ui(self) -> None:
        tabs = QTabWidget()
        self.setCentralWidget(tabs)

        self._control = ControlPanel()
        self._progress = ProgressTab()
        self._pages = PagesTab()
        self._issues = IssuesTab()
        self._duplicates = DuplicatesTab()

        tabs.addTab(self._control, "Control")
        tabs.addTab(self._progress, "Progress")
        tabs.addTab(self._pages, "Pages")
        tabs.addTab(self._issues, "Issues")
        tabs.addTab(self._duplicates, "Duplicates")
        self._tabs = tabs

        self._status_label = QLabel("Ready")
        status_bar = QStatusBar()
        status_bar.addWidget(self._status_label)
        self.setStatusBar(status_bar)

        self._bridge = EventBridge(self)
        self._bridge.progress.connect(self._on_progress)

        self._control.start_requested.connect(self._on_start)
        self._control.stop_requested.connect(self._on_stop)
        self._control.export_pages_requested.connect(self._on_export_pages)
        self._control.export_issues_requested.connect(self._on_export_issues)
        self._pages.page_selected.connect(self._on_page_selected)

    def _restore_recent_crawl(self) -> None:
        try:
            result = self._results_service.get_recent_crawl()
            if not result.success:
                self._set_status("No previous crawl found")
                return
            crawl = result.value
            crawl_id = getattr(crawl, "crawl_id", None)
            if crawl_id is None:
                self._set_status("No previous crawl found")
                return
            state = self._controller.refresh_results(crawl_id)
            self._sync_tables(state)
            created = getattr(crawl, "created_at", None)
            date_str = created.strftime("%Y-%m-%d %H:%M") if created else "unknown date"
            self._set_status(f"Restored crawl from {date_str}")
            self._control.set_export_enabled(True)
        except Exception:
            self._set_status("Could not restore recent crawl", error=True)
            traceback.print_exc()

    def _on_start(self, url: str, page_limit: int, timeout: int, same_host: bool) -> None:
        try:
            self._progress.reset()
            result = self._controller.start_crawl(url, same_host, page_limit, timeout)
            if not result.success:
                self._set_status(result.message or "Crawl failed to start", error=True)
                return
            crawl_id = self._controller.state.selected_crawl_id
            sub = self._event_delivery.subscribe(crawl_id, self._bridge.enqueue)
            if sub.success:
                self._subscription_id = sub.value.subscription_id
            self._control.set_crawl_active(True)
            self._control.set_export_enabled(False)
            self._set_status("Crawl started")
            self._tabs.setCurrentIndex(1)
        except Exception as exc:
            self._set_status(str(exc), error=True)
            traceback.print_exc()

    def _on_stop(self) -> None:
        try:
            self._controller.stop_crawl()
            self._set_status("Stop requested")
        except Exception as exc:
            self._set_status(str(exc), error=True)

    def _on_progress(self, event: CrawlProgressEvent) -> None:
        self._progress.update_from_event(event)
        terminal = event.kind in (
            CrawlProgressEventKind.CRAWL_COMPLETED,
            CrawlProgressEventKind.CRAWL_STOPPED,
            CrawlProgressEventKind.CRAWL_FAILED,
        )
        if terminal:
            self._control.set_crawl_active(False)
            self._unsubscribe()
            self._refresh_results()

    def _refresh_results(self) -> None:
        try:
            state = self._controller.refresh_results()
            self._sync_tables(state)
            self._control.set_export_enabled(self._controller.state.selected_crawl_id is not None)
            pages = len(state.pages)
            issues = len(state.issues)
            dups = len(state.duplicate_groups)
            self._progress.set_counts(pages=pages, issues=issues, dups=dups)
            self._set_status(f"Crawl complete — {pages} pages, {issues} issues, {dups} duplicate groups")
        except Exception as exc:
            self._set_status(str(exc), error=True)
            traceback.print_exc()

    def _sync_tables(self, state: object) -> None:
        self._pages.populate(state.pages)
        self._issues.populate(state.issues)
        self._duplicates.populate(state.duplicate_groups)

    def _on_page_selected(self, page_id: object) -> None:
        crawl_id = self._controller.state.selected_crawl_id
        if crawl_id is None:
            return
        try:
            result = self._results_service.get_page_detail(
                PageDetailQuery(crawl_id, page_id)
            )
            if not result.success:
                self._set_status(result.message or "Page not found", error=True)
                return
            dialog = PageDetailDialog(result.value, self)
            dialog.exec()
        except Exception as exc:
            self._set_status(str(exc), error=True)
            traceback.print_exc()

    def _on_export_pages(self, path: str) -> None:
        try:
            result = self._controller.export_pages(path)
            if result and result.success:
                self._set_status(f"Pages exported → {path}")
            else:
                msg = self._controller.state.last_error or "Export failed"
                self._set_status(msg, error=True)
        except Exception as exc:
            self._set_status(str(exc), error=True)

    def _on_export_issues(self, path: str) -> None:
        try:
            result = self._controller.export_issues(path)
            if result and result.success:
                self._set_status(f"Issues exported → {path}")
            else:
                msg = self._controller.state.last_error or "Export failed"
                self._set_status(msg, error=True)
        except Exception as exc:
            self._set_status(str(exc), error=True)

    def _unsubscribe(self) -> None:
        if self._subscription_id is not None:
            self._event_delivery.unsubscribe(self._subscription_id)
            self._subscription_id = None

    def _set_status(self, message: str, *, error: bool = False) -> None:
        self._status_label.setText(message)
        color = "red" if error else ""
        self._status_label.setStyleSheet(f"color: {color};")

    def closeEvent(self, event: object) -> None:
        self._unsubscribe()
        super().closeEvent(event)


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setApplicationName("xSEO")

    controller, results_svc, event_delivery = build_services()
    window = MainWindow(controller, results_svc, event_delivery)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
