"""End-to-end smoke test for the xseo desktop application.

The smoke test boots the real ``MainWindow`` (no mocks), runs a real crawl
against an in-process HTTP server, and verifies that every visible part of
the UI works:

  * Window opens, all tabs render.
  * "Start Crawl" launches a background crawl through the real wiring
    (SyncHttpFetchAdapter, SQLite persistence, threaded background,
    EventBridge, EventDelivery).
  * Progress events flow into the Progress tab.
  * On terminal event, pages/issues/duplicate tables populate.
  * Tabs can be switched without errors.
  * The Page Detail dialog opens for a crawled page.
  * CSV export writes a valid file.

All stderr writes, uncaught exceptions (main + background threads), and Qt log
messages are captured. Any "critical" Qt message or any uncaught exception
fails the test with a complete report so the user knows exactly what is broken.

Run::

    python3 -m pytest tests/smoke -q -s

Or directly as a script::

    python3 tests/smoke/test_ui_smoke.py
"""

from __future__ import annotations

import csv
import os
import sys
import time
import traceback
from pathlib import Path

# Ensure Qt loads before importing the rest so QT_QPA_PLATFORM applies.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# Allow running this file directly (python3 tests/smoke/test_ui_smoke.py) by
# adding the project root to sys.path so the ``tests.smoke._*`` imports resolve.
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from PySide6.QtCore import QCoreApplication, Qt
from PySide6.QtWidgets import QApplication

from tests.smoke._capture import CaptureContext, SmokeReport
from tests.smoke._fakesite import FakeSite
from xseo.application.events import CrawlProgressEventKind
from xseo.ui.app import MainWindow, build_services

CRAWL_TIMEOUT_SECONDS = 15.0
# How long to wait for the background worker to finish writing analysis
# (issues, then duplicate groups) after the crawl's CRAWL_COMPLETED event.
ANALYSIS_SETTLE_SECONDS = 10.0
EVENT_LOOP_TICK_MS = 50


def _qapp() -> QApplication:
    """Return the shared QApplication, creating it if needed."""
    app = QCoreApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
        app.setStyle("Fusion")
    return app


def _spin(app: QApplication, seconds: float) -> None:
    """Pump the Qt event loop for ``seconds`` so timers/signals fire."""
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        app.processEvents()
        time.sleep(EVENT_LOOP_TICK_MS / 1000.0)


def _wait_for_terminal(
    app: QApplication, terminal_kinds_seen: list, timeout: float
) -> bool:
    """Pump the event loop until a terminal crawl event is observed."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if terminal_kinds_seen:
            # let pending events (refresh_results, table populate) drain
            _spin(app, 0.5)
            return True
        time.sleep(EVENT_LOOP_TICK_MS / 1000.0)
    return False


def _run_smoke(tmp_dir: Path) -> tuple[SmokeReport, list[str]]:
    """Drive the application end-to-end; return capture report + extra defects."""
    defects: list[str] = []
    site = FakeSite().start()
    try:
        with CaptureContext() as report:
            app = _qapp()
            db_path = tmp_dir / "smoke.sqlite3"
            try:
                controller, results_service, event_delivery = build_services(db_path)
            except Exception:
                defects.append("build_services raised:\n" + traceback.format_exc())
                return report, defects

            window = MainWindow(controller, results_service, event_delivery)
            window.show()
            _spin(app, 0.2)

            # --- 1. Window + tab structure --------------------------------
            if window.windowTitle() != "xSEO — Local SEO Crawler":
                defects.append(f"unexpected window title: {window.windowTitle()!r}")
            expected_tabs = ["Control", "Progress", "Pages", "Issues", "Duplicates"]
            actual_tabs = [window._tabs.tabText(i) for i in range(window._tabs.count())]
            if actual_tabs != expected_tabs:
                defects.append(
                    f"tab labels mismatch: expected {expected_tabs}, got {actual_tabs}"
                )

            # Visit every tab to ensure each one renders without raising.
            for i in range(window._tabs.count()):
                window._tabs.setCurrentIndex(i)
                _spin(app, 0.05)

            # --- 2. Start a real crawl ------------------------------------
            terminal_kinds_seen: list[str] = []
            original_on_progress = window._on_progress

            def _instrumented_on_progress(event):  # noqa: ANN001
                try:
                    original_on_progress(event)
                except Exception:
                    defects.append(
                        f"_on_progress raised for {event.kind!r}:\n"
                        + traceback.format_exc()
                    )
                if event.kind in (
                    CrawlProgressEventKind.CRAWL_COMPLETED,
                    CrawlProgressEventKind.CRAWL_STOPPED,
                    CrawlProgressEventKind.CRAWL_FAILED,
                ):
                    terminal_kinds_seen.append(event.kind)

            window._bridge.progress.disconnect(window._on_progress)
            window._bridge.progress.connect(_instrumented_on_progress)

            window._control.url_input.setText(site.base_url)
            window._control.page_limit.setValue(20)
            window._control.timeout.setValue(5)
            window._control.same_host.setChecked(True)

            # Emit the same signal a button click would produce.
            try:
                window._control._on_start()
            except Exception:
                defects.append(
                    "ControlPanel._on_start raised:\n" + traceback.format_exc()
                )

            crawl_id = window._controller.state.selected_crawl_id
            if crawl_id is None:
                defects.append(
                    "after start_crawl, controller has no selected_crawl_id; "
                    f"last_error={window._controller.state.last_error!r}"
                )

            # Tap the event delivery directly so we see every event the UI sees
            # (including the silent-failure STATUS_CHANGED that the UI ignores).
            all_events: list[tuple[str, object, str | None]] = []
            if crawl_id is not None:
                event_delivery.subscribe(
                    crawl_id,
                    lambda e: all_events.append(
                        (str(e.kind), getattr(e.status, "value", e.status), e.message)
                    ),
                )

            # --- 3. Wait for terminal event --------------------------------
            ok = _wait_for_terminal(app, terminal_kinds_seen, CRAWL_TIMEOUT_SECONDS)
            if not ok:
                # The UI's terminal-event hook never fired. Inspect the background
                # thread for a silently-swallowed exception so we can report it.
                bg = controller.crawl_service.background_execution.get(crawl_id)
                bg_diag = "no background handle"
                if bg is not None:
                    coord_result = bg.result
                    bg_done = bg.done
                    bg_error = bg.error
                    coord_msg = getattr(coord_result, "message", None)
                    coord_ok = getattr(coord_result, "success", None)
                    bg_diag = (
                        f"done={bg_done} thread_error={bg_error!r} "
                        f"coordinator_success={coord_ok!r} "
                        f"coordinator_message={coord_msg!r}"
                    )
                defects.append(
                    f"UI never received a terminal CrawlProgressEvent "
                    f"after {CRAWL_TIMEOUT_SECONDS}s.\n"
                    f"  bg handle: {bg_diag}\n"
                    f"  event delivery saw: {all_events}\n"
                    f"  progress log: {window._progress._log.toPlainText()!r}"
                )
            elif CrawlProgressEventKind.CRAWL_FAILED in terminal_kinds_seen:
                defects.append(
                    f"crawl ended with CRAWL_FAILED; "
                    f"progress text={window._progress._log.toPlainText()!r}"
                )

            # --- 3b. Let analysis settle before reading the tables ---------
            # The engine publishes CRAWL_COMPLETED (which the UI refreshes on)
            # the moment the crawl finishes, but the background thread keeps
            # writing analysis afterwards — issues first, then duplicate groups
            # last. A refresh that lands mid-analysis sees a partial snapshot
            # (typically duplicates still empty), which is the classic flaky
            # failure on slower runners. Wait for the worker to fully finish,
            # then refresh once more so the assertions see settled tables.
            if ok and crawl_id is not None:
                bg = controller.crawl_service.background_execution.get(crawl_id)
                if bg is not None:
                    settle_deadline = time.monotonic() + ANALYSIS_SETTLE_SECONDS
                    while time.monotonic() < settle_deadline and not bg.done:
                        app.processEvents()
                        time.sleep(EVENT_LOOP_TICK_MS / 1000.0)
                window._refresh_results()
                _spin(app, 0.2)

            # --- 4. Tables populated ---------------------------------------
            pages_count = window._pages._table.rowCount()
            issues_count = window._issues._table.rowCount()
            dups_count = window._duplicates._table.rowCount()
            if pages_count == 0:
                defects.append("Pages table is empty after crawl")
            if issues_count == 0:
                defects.append(
                    "Issues table is empty — missing-title fixture should produce one"
                )
            if dups_count == 0:
                defects.append(
                    "Duplicates table is empty — / and /duplicate share a body"
                )

            # --- 5. Page detail dialog ------------------------------------
            if pages_count > 0:
                first_item = window._pages._table.item(0, 0)
                page_id = first_item.data(Qt.ItemDataRole.UserRole)
                try:
                    # Pre-empt the modal exec by opening through results_service
                    # then constructing the dialog manually.
                    from xseo.application.commands import PageDetailQuery
                    from xseo.ui.widgets.page_detail import PageDetailDialog

                    detail_result = results_service.get_page_detail(
                        PageDetailQuery(
                            window._controller.state.selected_crawl_id, page_id
                        )
                    )
                    if not detail_result.success:
                        defects.append(
                            f"get_page_detail failed: {detail_result.message}"
                        )
                    else:
                        dialog = PageDetailDialog(detail_result.value, window)
                        dialog.show()
                        _spin(app, 0.1)
                        dialog.close()
                except Exception:
                    defects.append(
                        "PageDetailDialog construction raised:\n"
                        + traceback.format_exc()
                    )

            # --- 6. CSV export --------------------------------------------
            pages_csv = tmp_dir / "pages.csv"
            issues_csv = tmp_dir / "issues.csv"
            try:
                window._on_export_pages(str(pages_csv))
            except Exception:
                defects.append("_on_export_pages raised:\n" + traceback.format_exc())
            try:
                window._on_export_issues(str(issues_csv))
            except Exception:
                defects.append("_on_export_issues raised:\n" + traceback.format_exc())

            if not pages_csv.exists():
                defects.append(f"pages CSV was not written to {pages_csv}")
            else:
                with pages_csv.open(newline="", encoding="utf-8") as fh:
                    rows = list(csv.DictReader(fh))
                if len(rows) != pages_count:
                    defects.append(
                        f"pages CSV row count {len(rows)} != table rows {pages_count}"
                    )

            if not issues_csv.exists():
                defects.append(f"issues CSV was not written to {issues_csv}")

            # --- 7. Restore-recent-crawl flow on a second window ----------
            try:
                window2 = MainWindow(controller, results_service, event_delivery)
                window2.show()
                _spin(app, 0.2)
                if not window2._control.export_pages_btn.isEnabled():
                    defects.append(
                        "second window did not restore recent crawl "
                        "(export pages stayed disabled)"
                    )
                window2.close()
            except Exception:
                defects.append(
                    "second MainWindow (restore recent) raised:\n"
                    + traceback.format_exc()
                )

            window.close()
            _spin(app, 0.1)

        return report, defects
    finally:
        site.stop()


def test_ui_smoke(tmp_path):
    report, defects = _run_smoke(tmp_path)
    failure_summary = report.summary()
    extra = "\n".join(defects)
    if defects or report.has_failures:
        raise AssertionError(
            "SMOKE TEST FOUND DEFECTS\n\n"
            f"=== captured ===\n{failure_summary}\n\n"
            f"=== behavior defects ({len(defects)}) ===\n{extra}\n"
        )


if __name__ == "__main__":
    # Standalone runner: prints a diagnostic report and exits non-zero on defects.
    import tempfile

    with tempfile.TemporaryDirectory() as td:
        report, defects = _run_smoke(Path(td))
        print("\n=== XSEO SMOKE REPORT ===")
        print(report.summary())
        print(f"\n=== behavior defects ({len(defects)}) ===")
        for d in defects:
            print("\n- " + d)
        bad = bool(defects) or report.has_failures
        print("\nRESULT:", "FAIL" if bad else "PASS")
        sys.exit(1 if bad else 0)
