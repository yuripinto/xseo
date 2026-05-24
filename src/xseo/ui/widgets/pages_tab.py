"""Pages tab: sortable table of crawled pages with double-click for detail."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

from xseo.application.read_models import PageRow

_COLUMNS: tuple[tuple[str, str], ...] = (
    ("URL", "url"),
    ("Final URL", "final_url"),
    ("Status", "status_code"),
    ("Title", "title"),
    ("Meta Description", "meta_description"),
    ("Canonical URL", "canonical_url"),
    ("Words", "word_count"),
    ("Content-Type", "content_type"),
)


class _NumericItem(QTableWidgetItem):
    """QTableWidgetItem that sorts numerically."""

    def __init__(self, value: int | None) -> None:
        super().__init__(str(value) if value is not None else "")
        self._value = value if value is not None else -1

    def __lt__(self, other: QTableWidgetItem) -> bool:
        if isinstance(other, _NumericItem):
            return self._value < other._value
        return super().__lt__(other)


class PagesTab(QWidget):
    page_selected: Signal = Signal(object)

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
        self._table.doubleClicked.connect(self._on_double_click)
        root.addWidget(self._table)

    def populate(self, rows: tuple[PageRow, ...]) -> None:
        self._table.setSortingEnabled(False)
        self._table.setRowCount(len(rows))
        for row_idx, row in enumerate(rows):
            for col_idx, (_, attr) in enumerate(_COLUMNS):
                raw = getattr(row, attr, None)
                if attr in ("status_code", "word_count"):
                    item: QTableWidgetItem = _NumericItem(raw)
                else:
                    text = getattr(raw, "value", raw) if raw is not None else ""
                    item = QTableWidgetItem(str(text))
                if col_idx == 0:
                    # page_id stored on the first column item so it survives sorting
                    item.setData(Qt.ItemDataRole.UserRole, row.page_id)
                self._table.setItem(row_idx, col_idx, item)
        self._table.setSortingEnabled(True)
        self._table.resizeColumnsToContents()

    def _on_double_click(self, index: object) -> None:
        row = self._table.currentRow()
        if row >= 0:
            first = self._table.item(row, 0)
            if first is not None:
                page_id = first.data(Qt.ItemDataRole.UserRole)
                if page_id is not None:
                    self.page_selected.emit(page_id)
