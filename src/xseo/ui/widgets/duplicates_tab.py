"""Duplicates tab: sortable table of exact-duplicate page groups."""

from __future__ import annotations

from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from xseo.application.read_models import DuplicateGroupRow
from xseo.ui.widgets.pages_tab import _NumericItem

_COLUMNS: tuple[tuple[str, str], ...] = (
    ("Content Hash", "content_hash"),
    ("Page Count", "page_count"),
    ("Representative URL", "representative_url"),
)


class DuplicatesTab(QWidget):
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

    def populate(self, rows: tuple[DuplicateGroupRow, ...]) -> None:
        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(rows))
        for row_idx, row in enumerate(rows):
            for col_idx, (_, attr) in enumerate(_COLUMNS):
                raw = getattr(row, attr, None)
                if attr == "page_count":
                    item: QTableWidgetItem = _NumericItem(raw)
                elif attr == "content_hash":
                    hash_val = getattr(raw, "value", str(raw)) if raw is not None else ""
                    item = QTableWidgetItem(str(hash_val)[:16] + "…" if len(str(hash_val)) > 16 else str(hash_val))
                else:
                    text = getattr(raw, "value", raw) if raw is not None else ""
                    item = QTableWidgetItem(str(text))
                self._table.setItem(row_idx, col_idx, item)
        self._table.setSortingEnabled(True)
        self._table.resizeColumnsToContents()
