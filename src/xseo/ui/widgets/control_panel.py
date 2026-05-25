"""Control panel: crawl configuration + start/stop + export buttons."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class ControlPanel(QWidget):
    start_requested: Signal = Signal(str, int, int, bool)
    stop_requested: Signal = Signal()
    export_pages_requested: Signal = Signal(str)
    export_issues_requested: Signal = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(12)

        crawl_group = QGroupBox("Crawl Configuration")
        form = QFormLayout(crawl_group)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://example.com/")
        form.addRow("Start URL:", self.url_input)

        self.page_limit = QSpinBox()
        self.page_limit.setRange(1, 100_000)
        self.page_limit.setValue(500)
        form.addRow("Page limit:", self.page_limit)

        self.timeout = QSpinBox()
        self.timeout.setRange(1, 120)
        self.timeout.setValue(10)
        self.timeout.setSuffix(" s")
        form.addRow("Timeout:", self.timeout)

        self.request_delay = QDoubleSpinBox()
        self.request_delay.setRange(0.0, 60.0)
        self.request_delay.setSingleStep(0.1)
        self.request_delay.setDecimals(1)
        self.request_delay.setValue(0.5)
        self.request_delay.setSuffix(" s")
        form.addRow("Request delay:", self.request_delay)

        self.same_host = QCheckBox("Same host only")
        self.same_host.setChecked(True)
        form.addRow("", self.same_host)

        self.respect_robots = QCheckBox("Respect robots.txt")
        self.respect_robots.setChecked(True)
        form.addRow("", self.respect_robots)

        root.addWidget(crawl_group)

        btn_row = QHBoxLayout()
        self.start_btn = QPushButton("Start Crawl")
        self.start_btn.setDefault(True)
        self.stop_btn = QPushButton("Stop Crawl")
        self.stop_btn.setEnabled(False)
        btn_row.addWidget(self.start_btn)
        btn_row.addWidget(self.stop_btn)
        root.addLayout(btn_row)

        export_group = QGroupBox("Export")
        export_layout = QHBoxLayout(export_group)
        self.export_pages_btn = QPushButton("Export Pages…")
        self.export_pages_btn.setEnabled(False)
        self.export_issues_btn = QPushButton("Export Issues…")
        self.export_issues_btn.setEnabled(False)
        export_layout.addWidget(self.export_pages_btn)
        export_layout.addWidget(self.export_issues_btn)
        root.addWidget(export_group)

        root.addStretch()

        self.start_btn.clicked.connect(self._on_start)
        self.stop_btn.clicked.connect(self.stop_requested)
        self.export_pages_btn.clicked.connect(self._on_export_pages)
        self.export_issues_btn.clicked.connect(self._on_export_issues)

    def set_crawl_active(self, active: bool) -> None:
        self.start_btn.setEnabled(not active)
        self.stop_btn.setEnabled(active)

    def set_export_enabled(self, enabled: bool) -> None:
        self.export_pages_btn.setEnabled(enabled)
        self.export_issues_btn.setEnabled(enabled)

    def _on_start(self) -> None:
        url = self.url_input.text().strip()
        if not url:
            return
        self.start_requested.emit(url, self.page_limit.value(), self.timeout.value(), self.same_host.isChecked())

    def _on_export_pages(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export Pages", "pages.csv", "CSV (*.csv)")
        if path:
            self.export_pages_requested.emit(path)

    def _on_export_issues(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export Issues", "issues.csv", "CSV (*.csv)")
        if path:
            self.export_issues_requested.emit(path)
