"""Progress tab: live crawl event feed and counters."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QLabel,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from xseo.application.events import CrawlProgressEvent, CrawlProgressEventKind

_TERMINAL_KINDS = (
    CrawlProgressEventKind.CRAWL_COMPLETED,
    CrawlProgressEventKind.CRAWL_STOPPED,
    CrawlProgressEventKind.CRAWL_FAILED,
)


class ProgressTab(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._live_pages: int = 0
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        stats_group = QGroupBox("Crawl Statistics")
        form = QFormLayout(stats_group)
        self._status_label = QLabel("—")
        self._pages_label = QLabel("0")
        self._errors_label = QLabel("0")
        self._issues_label = QLabel("0")
        self._dups_label = QLabel("0")
        self._url_label = QLabel("—")
        self._url_label.setWordWrap(True)
        form.addRow("Status:", self._status_label)
        form.addRow("Pages crawled:", self._pages_label)
        form.addRow("Errors:", self._errors_label)
        form.addRow("Issues:", self._issues_label)
        form.addRow("Duplicate groups:", self._dups_label)
        form.addRow("Current URL:", self._url_label)
        root.addWidget(stats_group)

        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setMaximumBlockCount(500)
        root.addWidget(self._log)

    def update_from_event(self, event: CrawlProgressEvent) -> None:
        self._status_label.setText(str(getattr(event.status, "value", event.status)))
        if event.kind == CrawlProgressEventKind.PAGE_FETCHED:
            self._live_pages += 1
            self._pages_label.setText(str(self._live_pages))
        if event.message:
            self._log.appendPlainText(event.message)
        if event.kind in _TERMINAL_KINDS:
            self._url_label.setText("—")
        elif event.message:
            self._url_label.setText(event.message)

    def reset(self) -> None:
        self._live_pages = 0
        self._status_label.setText("—")
        self._pages_label.setText("0")
        self._errors_label.setText("0")
        self._issues_label.setText("0")
        self._dups_label.setText("0")
        self._url_label.setText("—")
        self._log.clear()

    def set_counts(
        self, pages: int = 0, errors: int = 0, issues: int = 0, dups: int = 0
    ) -> None:
        self._pages_label.setText(str(pages))
        self._errors_label.setText(str(errors))
        self._issues_label.setText(str(issues))
        self._dups_label.setText(str(dups))
