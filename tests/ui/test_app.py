"""Smoke tests for PySide6 UI components."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

from xseo.application.events import CrawlProgressEvent, CrawlProgressEventKind
from xseo.application.read_models import DuplicateGroupRow, IssueRow, PageRow
from xseo.application.results import ApplicationResult
from xseo.domain.enums import CrawlStatus, IssueSeverity, IssueType
from xseo.domain.ids import DuplicateGroupId, IssueId, PageId
from xseo.domain.urls import NormalizedUrl
from xseo.domain.value_objects import ContentHash
from xseo.ui.desktop import DesktopState

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _url(v: str) -> object:
    return NormalizedUrl.create(v).value


def _page_id(v: str) -> object:
    return PageId.create(v).value


def _page_row(
    page_id: str = "p-1", url: str = "https://example.com/", status: int = 200
) -> PageRow:
    return PageRow(
        page_id=_page_id(page_id),
        url=_url(url),
        final_url=_url(url),
        status_code=status,
        title=f"Title {page_id}",
        meta_description="Desc",
        canonical_url=None,
        word_count=100,
        content_type="text/html",
    )


def _issue_row(
    issue_id: str = "i-1", severity: IssueSeverity = IssueSeverity.HIGH
) -> IssueRow:
    return IssueRow(
        issue_id=IssueId.create(issue_id).value,
        affected_url=_url("https://example.com/"),
        issue_type=IssueType.TITLE_MISSING,
        severity=severity,
        explanation="Missing title",
    )


def _dup_row() -> DuplicateGroupRow:
    return DuplicateGroupRow(
        duplicate_group_id=DuplicateGroupId.create("dg-1").value,
        content_hash=ContentHash.create("abc123").value,
        page_count=2,
        representative_url=_url("https://example.com/"),
    )


def _progress_event(
    kind: CrawlProgressEventKind = CrawlProgressEventKind.PAGE_FETCHED,
    status: CrawlStatus = CrawlStatus.RUNNING,
    message: str | None = "Fetched https://example.com/",
    crawl_id: str = "crawl-1",
) -> CrawlProgressEvent:
    return CrawlProgressEvent(
        crawl_id=crawl_id,
        kind=kind,
        status=status,
        occurred_at=datetime.now(UTC),
        message=message,
    )


def _fake_desktop_state(**kwargs) -> DesktopState:
    defaults = dict(
        selected_crawl_id=None,
        crawl_status=None,
        pages=(),
        issues=(),
        duplicate_groups=(),
        busy=False,
        last_error=None,
        export_status=None,
    )
    defaults.update(kwargs)
    return DesktopState(**defaults)


def _make_controller(
    *,
    start_ok: bool = True,
    stop_ok: bool = True,
    state: DesktopState | None = None,
) -> MagicMock:
    ctrl = MagicMock()
    crawl_id = _page_id("crawl-1")

    if start_ok:
        from xseo.application.read_models import CrawlSession

        session = CrawlSession(crawl_id=crawl_id, status=CrawlStatus.RUNNING)
        ctrl.start_crawl.return_value = ApplicationResult.ok(session)
    else:
        ctrl.start_crawl.return_value = ApplicationResult.fail(
            "Invalid URL", "crawl.invalid"
        )

    if stop_ok:
        ctrl.stop_crawl.return_value = ApplicationResult.ok(None)
    else:
        ctrl.stop_crawl.return_value = ApplicationResult.fail(
            "Stop failed", "crawl.stop_failed"
        )

    _state = state or _fake_desktop_state(selected_crawl_id=crawl_id)
    ctrl.state = _state
    ctrl.refresh_results.return_value = _state
    return ctrl


def _make_results_service(*, recent_crawl=None) -> MagicMock:
    svc = MagicMock()
    if recent_crawl is None:
        svc.get_recent_crawl.return_value = ApplicationResult.fail(
            "none", "crawl.no_recent"
        )
    else:
        svc.get_recent_crawl.return_value = ApplicationResult.ok(recent_crawl)
    svc.list_pages.return_value = ApplicationResult.ok(())
    svc.list_issues.return_value = ApplicationResult.ok(())
    svc.list_duplicate_groups.return_value = ApplicationResult.ok(())
    return svc


def _make_event_delivery() -> MagicMock:
    svc = MagicMock()
    sub = MagicMock()
    sub.subscription_id = "sub-1"
    svc.subscribe.return_value = ApplicationResult.ok(sub)
    return svc


def _make_window(qapp, *, state=None, start_ok=True, stop_ok=True, recent_crawl=None):
    from xseo.ui.app import MainWindow

    ctrl = _make_controller(start_ok=start_ok, stop_ok=stop_ok, state=state)
    results = _make_results_service(recent_crawl=recent_crawl)
    events = _make_event_delivery()
    return MainWindow(ctrl, results, events), ctrl, results, events


# ---------------------------------------------------------------------------
# ControlPanel
# ---------------------------------------------------------------------------


def test_control_panel_initial_state(qapp):
    from xseo.ui.widgets.control_panel import ControlPanel

    panel = ControlPanel()
    assert panel.start_btn.isEnabled()
    assert not panel.stop_btn.isEnabled()
    assert not panel.export_pages_btn.isEnabled()
    assert not panel.export_issues_btn.isEnabled()
    assert panel.page_limit.value() == 500
    assert panel.timeout.value() == 10
    assert panel.same_host.isChecked()


def test_control_panel_set_crawl_active(qapp):
    from xseo.ui.widgets.control_panel import ControlPanel

    panel = ControlPanel()
    panel.set_crawl_active(True)
    assert not panel.start_btn.isEnabled()
    assert panel.stop_btn.isEnabled()

    panel.set_crawl_active(False)
    assert panel.start_btn.isEnabled()
    assert not panel.stop_btn.isEnabled()


def test_control_panel_empty_url_does_not_emit(qapp, qtbot):
    from xseo.ui.widgets.control_panel import ControlPanel

    panel = ControlPanel()
    panel.url_input.setText("")
    signals = []
    panel.start_requested.connect(lambda *a: signals.append(a))
    qtbot.mouseClick(
        panel.start_btn,
        __import__("PySide6.QtCore", fromlist=["Qt"]).Qt.MouseButton.LeftButton,
    )
    assert signals == [], "start_requested must not fire with empty URL"


def test_control_panel_valid_url_emits_start(qapp, qtbot):
    from xseo.ui.widgets.control_panel import ControlPanel

    panel = ControlPanel()
    panel.url_input.setText("https://example.com/")
    signals = []
    panel.start_requested.connect(lambda *a: signals.append(a))
    qtbot.mouseClick(
        panel.start_btn,
        __import__("PySide6.QtCore", fromlist=["Qt"]).Qt.MouseButton.LeftButton,
    )
    assert len(signals) == 1
    url, page_limit, timeout, same_host = signals[0]
    assert url == "https://example.com/"
    assert page_limit == 500
    assert timeout == 10
    assert same_host is True


def test_control_panel_export_enabled_toggle(qapp):
    from xseo.ui.widgets.control_panel import ControlPanel

    panel = ControlPanel()
    panel.set_export_enabled(True)
    assert panel.export_pages_btn.isEnabled()
    assert panel.export_issues_btn.isEnabled()

    panel.set_export_enabled(False)
    assert not panel.export_pages_btn.isEnabled()
    assert not panel.export_issues_btn.isEnabled()


# ---------------------------------------------------------------------------
# ProgressTab
# ---------------------------------------------------------------------------


def test_progress_tab_reset_clears_all(qapp):
    from xseo.ui.widgets.progress_tab import ProgressTab

    tab = ProgressTab()
    tab.set_counts(pages=5, errors=2, issues=3, dups=1)
    tab._status_label.setText("running")
    tab.reset()
    assert tab._status_label.text() == "—"
    assert tab._pages_label.text() == "0"
    assert tab._errors_label.text() == "0"
    assert tab._issues_label.text() == "0"
    assert tab._dups_label.text() == "0"
    assert tab._url_label.text() == "—"


def test_progress_tab_update_from_page_fetched_event(qapp):
    from xseo.ui.widgets.progress_tab import ProgressTab

    tab = ProgressTab()
    event = _progress_event(
        kind=CrawlProgressEventKind.PAGE_FETCHED,
        message="Fetched url (3 pages, 0 errors)",
    )
    tab.update_from_event(event)
    assert tab._status_label.text() == "running"
    assert "3 pages" in tab._log.toPlainText()


def test_progress_tab_live_page_counter_increments(qapp):
    """Counter labels must update during crawl, not only after completion."""
    from xseo.ui.widgets.progress_tab import ProgressTab

    tab = ProgressTab()
    for i in range(1, 4):
        event = _progress_event(
            kind=CrawlProgressEventKind.PAGE_FETCHED,
            message=f"Fetched url ({i} pages, 0 errors)",
        )
        tab.update_from_event(event)
    assert tab._pages_label.text() == "3", "pages_label must reflect live page count"


def test_progress_tab_terminal_event_resets_url_label(qapp):
    from xseo.ui.widgets.progress_tab import ProgressTab

    tab = ProgressTab()
    tab.update_from_event(_progress_event(message="current url"))
    assert tab._url_label.text() != "—"

    tab.update_from_event(
        _progress_event(
            kind=CrawlProgressEventKind.CRAWL_COMPLETED,
            status=CrawlStatus.COMPLETED,
            message="Done",
        )
    )
    assert tab._url_label.text() == "—", "URL label must be cleared on terminal event"


def test_progress_tab_set_counts(qapp):
    from xseo.ui.widgets.progress_tab import ProgressTab

    tab = ProgressTab()
    tab.set_counts(pages=10, errors=2, issues=5, dups=3)
    assert tab._pages_label.text() == "10"
    assert tab._errors_label.text() == "2"
    assert tab._issues_label.text() == "5"
    assert tab._dups_label.text() == "3"


# ---------------------------------------------------------------------------
# PagesTab — including sort-stability of page_id selection
# ---------------------------------------------------------------------------


def test_pages_tab_populate_row_count(qapp):
    from xseo.ui.widgets.pages_tab import PagesTab

    tab = PagesTab()
    tab.populate((_page_row("p-1"), _page_row("p-2")))
    assert tab._table.rowCount() == 2


def test_pages_tab_double_click_emits_correct_page_id(qapp, qtbot):
    """Emitted page_id must match the UserRole data of the visually selected row,
    regardless of what sort order the table is currently in."""
    from PySide6.QtCore import Qt

    from xseo.ui.widgets.pages_tab import PagesTab

    tab = PagesTab()
    rows = (_page_row("p-1", "https://a.com/"), _page_row("p-2", "https://b.com/"))
    tab.populate(rows)

    selected = []
    tab.page_selected.connect(selected.append)

    tab._table.selectRow(0)
    expected_page_id = tab._table.item(0, 0).data(Qt.ItemDataRole.UserRole)
    tab._table.doubleClicked.emit(tab._table.currentIndex())

    assert len(selected) == 1
    assert selected[0] is expected_page_id, (
        "double-click must emit the page_id stored in UserRole for the current visual row"
    )


def test_pages_tab_page_id_correct_after_sort(qapp, qtbot):
    """After sorting the table by status code, double-clicking a row must
    open the page detail for the *visually selected* row, not the original row."""
    from PySide6.QtCore import Qt

    from xseo.ui.widgets.pages_tab import PagesTab

    tab = PagesTab()
    rows = (
        _page_row("p-1", "https://a.com/", status=200),
        _page_row("p-2", "https://b.com/", status=404),
        _page_row("p-3", "https://c.com/", status=301),
    )
    tab.populate(rows)

    # Sort by Status column (index 2) descending → 404, 301, 200
    tab._table.horizontalHeader().setSortIndicator(2, Qt.SortOrder.DescendingOrder)
    tab._table.sortItems(2, Qt.SortOrder.DescendingOrder)

    # First visual row after sort is status=404 → page p-2
    tab._table.selectRow(0)
    selected = []
    tab.page_selected.connect(selected.append)
    tab._table.doubleClicked.emit(tab._table.currentIndex())

    assert len(selected) == 1
    assert str(getattr(selected[0], "value", selected[0])) == "p-2", (
        "After descending sort, visual row 0 is status=404 (p-2), not p-1"
    )


def test_pages_tab_empty_populate_no_crash(qapp):
    from xseo.ui.widgets.pages_tab import PagesTab

    tab = PagesTab()
    tab.populate(())
    assert tab._table.rowCount() == 0


# ---------------------------------------------------------------------------
# IssuesTab
# ---------------------------------------------------------------------------


def test_issues_tab_no_severity_background(qapp):
    from PySide6.QtCore import Qt

    from xseo.ui.widgets.issues_tab import IssuesTab

    tab = IssuesTab()
    tab.populate(
        (
            _issue_row("i-1", IssueSeverity.HIGH),
            _issue_row("i-2", IssueSeverity.MEDIUM),
            _issue_row("i-3", IssueSeverity.LOW),
        )
    )
    assert tab._table.rowCount() == 3
    for row_idx in range(3):
        brush = tab._table.item(row_idx, 0).background()
        assert brush.style() == Qt.BrushStyle.NoBrush, (
            "Issue rows must not have a tinted background regardless of severity"
        )


# ---------------------------------------------------------------------------
# DuplicatesTab
# ---------------------------------------------------------------------------


def test_duplicates_tab_populate(qapp):
    from xseo.ui.widgets.duplicates_tab import DuplicatesTab

    tab = DuplicatesTab()
    tab.populate((_dup_row(),))
    assert tab._table.rowCount() == 1


# ---------------------------------------------------------------------------
# EventBridge
# ---------------------------------------------------------------------------


def test_event_bridge_drains_queue_to_signal(qapp, qtbot):
    from xseo.ui.bridge import EventBridge

    bridge = EventBridge()
    received = []
    bridge.progress.connect(received.append)

    event = _progress_event()
    with qtbot.waitSignal(bridge.progress, timeout=1000):
        bridge.enqueue(event)
    assert received == [event]


def test_event_bridge_multiple_events_drained_in_order(qapp, qtbot):
    from xseo.ui.bridge import EventBridge

    bridge = EventBridge()
    received = []
    bridge.progress.connect(received.append)

    events = [_progress_event(message=f"msg-{i}") for i in range(5)]
    for e in events:
        bridge.enqueue(e)
    qtbot.waitSignal(bridge.progress, timeout=1000)
    # give one more drain cycle
    qtbot.wait(300)
    assert received == events


# ---------------------------------------------------------------------------
# MainWindow integration
# ---------------------------------------------------------------------------


def test_main_window_starts_clean(qapp, tmp_path):
    from xseo.ui.app import MainWindow, build_services

    ctrl, results, events = build_services(tmp_path / "t.sqlite3")
    w = MainWindow(ctrl, results, events)
    assert w.windowTitle() == "xSEO — Local SEO Crawler"
    assert w._status_label.text() == "No previous crawl found"
    assert not w._control.export_pages_btn.isEnabled()


def test_main_window_start_crawl_switches_to_progress_tab(qapp):
    w, ctrl, results, events = _make_window(qapp)
    w._on_start("https://example.com/", 100, 10, True)
    assert w._tabs.currentIndex() == 1


def test_main_window_start_crawl_disables_start_enables_stop(qapp):
    w, ctrl, results, events = _make_window(qapp)
    w._on_start("https://example.com/", 100, 10, True)
    assert not w._control.start_btn.isEnabled()
    assert w._control.stop_btn.isEnabled()


def test_main_window_start_crawl_failure_shows_error(qapp):
    w, ctrl, results, events = _make_window(qapp, start_ok=False)
    w._on_start("bad-url", 100, 10, True)
    assert "red" in w._status_label.styleSheet()
    assert w._control.start_btn.isEnabled(), (
        "start button must stay enabled after failure"
    )
    assert not w._control.stop_btn.isEnabled()


def test_main_window_stop_crawl_shows_status(qapp):
    w, ctrl, results, events = _make_window(qapp)
    w._on_start("https://example.com/", 100, 10, True)
    w._on_stop()
    assert w._status_label.text() == "Stop requested"


def test_main_window_stop_crawl_failure_shows_error(qapp):
    """If controller reports last_error after stop, the status bar must reflect it."""
    error_state = _fake_desktop_state(
        selected_crawl_id=_page_id("crawl-1"),
        last_error="No crawl selected",
    )
    w, ctrl, _, _ = _make_window(qapp, stop_ok=False, state=error_state)
    ctrl.stop_crawl.return_value = (
        None  # controller sets last_error instead of returning result
    )
    ctrl.state = error_state
    w._on_stop()
    # Should show the last_error, not "Stop requested"
    assert (
        w._status_label.text() != "Stop requested"
        or "red" not in w._status_label.styleSheet()
    )


def test_main_window_terminal_event_re_enables_start(qapp):
    completed_state = _fake_desktop_state(
        selected_crawl_id=_page_id("crawl-1"),
        pages=(_page_row(),),
        issues=(),
        duplicate_groups=(),
    )
    w, ctrl, _, _ = _make_window(qapp, state=completed_state)
    ctrl.refresh_results.return_value = completed_state

    w._on_start("https://example.com/", 100, 10, True)
    assert not w._control.start_btn.isEnabled()

    event = _progress_event(
        kind=CrawlProgressEventKind.CRAWL_COMPLETED, status=CrawlStatus.COMPLETED
    )
    w._on_progress(event)

    assert w._control.start_btn.isEnabled(), (
        "Start must be re-enabled after crawl completes"
    )
    assert not w._control.stop_btn.isEnabled()


def test_main_window_terminal_event_populates_tables(qapp):
    pages = (_page_row("p-1"), _page_row("p-2"))
    issues = (_issue_row("i-1"), _issue_row("i-2", IssueSeverity.MEDIUM))
    dups = (_dup_row(),)
    done_state = _fake_desktop_state(
        selected_crawl_id=_page_id("crawl-1"),
        pages=pages,
        issues=issues,
        duplicate_groups=dups,
    )
    w, ctrl, _, _ = _make_window(qapp, state=done_state)
    ctrl.refresh_results.return_value = done_state

    w._on_start("https://example.com/", 100, 10, True)
    w._on_progress(
        _progress_event(
            kind=CrawlProgressEventKind.CRAWL_COMPLETED, status=CrawlStatus.COMPLETED
        )
    )

    assert w._pages._table.rowCount() == 2
    assert w._issues._table.rowCount() == 2
    assert w._duplicates._table.rowCount() == 1


def test_main_window_terminal_event_enables_export(qapp):
    done_state = _fake_desktop_state(selected_crawl_id=_page_id("crawl-1"))
    w, ctrl, _, _ = _make_window(qapp, state=done_state)
    ctrl.refresh_results.return_value = done_state

    w._on_start("https://example.com/", 100, 10, True)
    assert not w._control.export_pages_btn.isEnabled()

    w._on_progress(
        _progress_event(
            kind=CrawlProgressEventKind.CRAWL_COMPLETED, status=CrawlStatus.COMPLETED
        )
    )
    assert w._control.export_pages_btn.isEnabled()


def test_main_window_status_bar_error_is_red(qapp):
    w, _, _, _ = _make_window(qapp)
    w._set_status("Something broke", error=True)
    assert "red" in w._status_label.styleSheet()
    assert w._status_label.text() == "Something broke"


def test_main_window_status_bar_normal_has_no_color(qapp):
    w, _, _, _ = _make_window(qapp)
    w._set_status("Something broke", error=True)
    w._set_status("All good")
    assert "red" not in w._status_label.styleSheet()


def test_main_window_page_detail_no_crawl_id_safe(qapp):
    """Selecting a page when no crawl is active must not raise."""
    no_crawl_state = _fake_desktop_state(selected_crawl_id=None)
    w, ctrl, _, _ = _make_window(qapp, state=no_crawl_state)
    ctrl.state = no_crawl_state
    w._on_page_selected(_page_id("p-1"))  # must not raise


def test_main_window_export_pages_success(qapp, tmp_path):
    from xseo.application.results import ExportStatus

    path = str(tmp_path / "pages.csv")
    done_state = _fake_desktop_state(selected_crawl_id=_page_id("crawl-1"))
    w, ctrl, _, _ = _make_window(qapp, state=done_state)
    ctrl.export_pages.return_value = ApplicationResult.ok(
        ExportStatus(success=True, row_count=3)
    )
    w._on_export_pages(path)
    assert f"Pages exported → {path}" == w._status_label.text()


def test_main_window_export_pages_failure_shows_error(qapp, tmp_path):
    path = str(tmp_path / "pages.csv")
    err_state = _fake_desktop_state(
        selected_crawl_id=_page_id("crawl-1"),
        last_error="Export failed: permission denied",
    )
    w, ctrl, _, _ = _make_window(qapp, state=err_state)
    ctrl.export_pages.return_value = ApplicationResult.fail(
        "permission denied", "export.failed"
    )
    ctrl.state = err_state
    w._on_export_pages(path)
    assert "red" in w._status_label.styleSheet()


def test_main_window_crawl_failed_event_re_enables_start(qapp):
    w, ctrl, _, _ = _make_window(qapp)
    ctrl.refresh_results.return_value = _fake_desktop_state(
        selected_crawl_id=_page_id("crawl-1")
    )
    w._on_start("https://example.com/", 100, 10, True)
    w._on_progress(
        _progress_event(
            kind=CrawlProgressEventKind.CRAWL_FAILED, status=CrawlStatus.FAILED
        )
    )
    assert w._control.start_btn.isEnabled()


def test_build_services_wires_all_components(tmp_path):
    from xseo.ui.app import build_services

    ctrl, results, events = build_services(tmp_path / "t.sqlite3")
    assert ctrl is not None
    assert results is not None
    assert events is not None
