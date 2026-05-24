"""Page detail modal dialog."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from xseo.application.read_models import PageDetail


class PageDetailDialog(QDialog):
    def __init__(self, detail: PageDetail, parent: QWidget | None = None) -> None:
        url_str = getattr(detail.page.url, "value", str(detail.page.url))
        super().__init__(parent)
        self.setWindowTitle(url_str)
        self.setMinimumWidth(700)
        self._build_ui(detail)
        screen = self.screen()
        if screen is not None:
            self.setMaximumHeight(int(screen.availableGeometry().height() * 0.8))

    def _build_ui(self, detail: PageDetail) -> None:
        outer = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        layout = QVBoxLayout(inner)
        scroll.setWidget(inner)
        outer.addWidget(scroll)

        page = detail.page
        form = QFormLayout()
        form.addRow("URL:", QLabel(_text(page.url)))
        form.addRow("Final URL:", QLabel(_text(page.final_url)))
        form.addRow("Status code:", QLabel(str(page.status_code)))
        form.addRow("Title:", QLabel(_text(page.title) or "—"))
        form.addRow("Meta description:", QLabel(_text(page.meta_description) or "—"))
        form.addRow("Canonical URL:", QLabel(_text(page.canonical_url) or "—"))
        form.addRow("Word count:", QLabel(str(page.word_count)))
        form.addRow("Content-Type:", QLabel(_text(page.content_type) or "—"))
        form.addRow("Content hash:", QLabel(_text(detail.content_hash) or "—"))
        layout.addLayout(form)

        layout.addWidget(_tree("Headings", detail.headings, _heading_cols))
        layout.addWidget(_tree("Outlinks", detail.outlinks, _link_cols))
        layout.addWidget(_tree("Redirects", detail.redirects, _redirect_cols))
        layout.addWidget(_tree("Issues", detail.issues, _issue_cols))

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        outer.addWidget(buttons)


def _text(value: object) -> str:
    if value is None:
        return ""
    return str(getattr(value, "value", value))


def _tree(title: str, items: tuple, col_factory: object) -> QTreeWidget:
    headers, row_fn = col_factory()
    tree = QTreeWidget()
    tree.setHeaderLabels([title] + list(headers))
    tree.setColumnCount(len(headers) + 1)
    tree.setSortingEnabled(True)
    for item in items:
        values = row_fn(item)
        node = QTreeWidgetItem([""] + [str(v) for v in values])
        tree.addTopLevelItem(node)
    tree.resizeColumnToContents(0)
    count = tree.topLevelItemCount()
    tree.setFixedHeight(min(max(60, count * 22 + 30), 200))
    tree.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    return tree


def _heading_cols() -> tuple:
    return (
        ("Level", "Text", "Position"),
        lambda h: (getattr(h.level, "value", h.level), h.text, h.position),
    )


def _link_cols() -> tuple:
    return (
        ("Target URL", "Relation", "Anchor", "Nofollow"),
        lambda lk: (
            _text(lk.target_url),
            getattr(lk.relation, "value", lk.relation),
            lk.anchor_text or "",
            "yes" if lk.nofollow else "no",
        ),
    )


def _redirect_cols() -> tuple:
    return (
        ("From URL", "To URL", "Status"),
        lambda r: (_text(r.from_url), _text(r.to_url), r.status_code),
    )


def _issue_cols() -> tuple:
    return (
        ("Type", "Severity", "Explanation"),
        lambda i: (
            getattr(i.issue_type, "value", i.issue_type),
            getattr(i.severity, "value", i.severity),
            i.explanation,
        ),
    )
