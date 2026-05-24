"""CSV export adapter."""

from __future__ import annotations

import csv
from hashlib import sha256
from pathlib import Path

from xseo.domain.entities import ExportResult
from xseo.domain.enums import ExportKind
from xseo.domain.ids import CrawlId, ExportId
from xseo.domain.value_objects import FilePath


PAGE_HEADERS = (
    "page_id",
    "url",
    "final_url",
    "status_code",
    "title",
    "meta_description",
    "canonical_url",
    "word_count",
    "content_type",
)

ISSUE_HEADERS = (
    "issue_id",
    "affected_url",
    "issue_type",
    "severity",
    "explanation",
    "page_id",
)


class CsvExportAdapter:
    def __init__(self, crawl_id=None):
        self.crawl_id = crawl_id or CrawlId.create("unknown-crawl").value

    def set_crawl_id(self, crawl_id):
        self.crawl_id = crawl_id
        return self

    def write_pages(self, target_path, rows):
        return self._write(target_path, rows, ExportKind.PAGES, PAGE_HEADERS)

    def write_issues(self, target_path, rows):
        return self._write(target_path, rows, ExportKind.ISSUES, ISSUE_HEADERS)

    def _write(self, target_path, rows, kind, headers):
        path = Path(target_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        row_tuple = tuple(rows)
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=headers)
            writer.writeheader()
            for row in row_tuple:
                writer.writerow({header: _cell(getattr(row, header, None)) for header in headers})
        return ExportResult.create(
            _export_id(kind, self.crawl_id, path, len(row_tuple)),
            self.crawl_id,
            kind,
            FilePath.create(str(path)).value,
            len(row_tuple),
            True,
        ).value


def _cell(value):
    if value is None:
        return ""
    return getattr(value, "value", value)


def _export_id(kind, crawl_id, path, row_count):
    crawl_value = getattr(crawl_id, "value", str(crawl_id))
    raw = f"{kind.value}|{crawl_value}|{path}|{row_count}"
    return ExportId.create("export-" + sha256(raw.encode("utf-8")).hexdigest()[:24]).value
