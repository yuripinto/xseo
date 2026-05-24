"""Issues tab: sortable table with severity color coding."""

from __future__ import annotations

from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from xseo.application.read_models import IssueRow

_COLUMNS: tuple[tuple[str, str], ...] = (
    ("Issue Type", "issue_type"),
    ("Severity", "severity"),
    ("Affected URL", "affected_url"),
    ("Explanation", "explanation"),
)


class IssuesTab(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        self._table = QTableWidget(0, len(_COLUMNS))
        self._table.setHorizontalHeaderLabels([label for label, _ in _COLUMNS])
        self._table.setSortingEnabled(True)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.horizontalHeader().setStretchLastSection(True)
        root.addWidget(self._table)

    def populate(self, rows: tuple[IssueRow, ...]) -> None:
        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(rows))
        for row_idx, row in enumerate(rows):
            for col_idx, (_, attr) in enumerate(_COLUMNS):
                raw = getattr(row, attr, None)
                text = getattr(raw, "value", raw) if raw is not None else ""
                item = QTableWidgetItem(str(text))
                self._table.setItem(row_idx, col_idx, item)
        self._table.setSortingEnabled(True)
        self._table.resizeColumnsToContents()
