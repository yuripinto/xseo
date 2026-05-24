import csv

from xseo.adapters.export import CsvExportAdapter
from xseo.application import ExportCommand
from xseo.application.read_models import IssueRow, PageRow
from xseo.application.services import ExportApplicationService
from xseo.domain.enums import ExportKind, IssueSeverity, IssueType
from xseo.domain.ids import CrawlId, IssueId, PageId
from xseo.domain.urls import NormalizedUrl


def _id(cls, value):
    return cls.create(value).value


def _url(value):
    return NormalizedUrl.create(value).value


def test_csv_exporter_writes_pages_with_stable_headers(tmp_path):
    path = tmp_path / "pages.csv"
    adapter = CsvExportAdapter(_id(CrawlId, "crawl-1"))
    row = PageRow(
        _id(PageId, "page-1"),
        _url("https://example.com/"),
        _url("https://example.com/"),
        200,
        "Home",
        None,
        None,
        120,
        "text/html",
    )

    result = adapter.write_pages(path, (row,))

    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.reader(handle))
    assert result.kind == ExportKind.PAGES
    assert result.row_count == 1
    assert rows[0] == list(("page_id", "url", "final_url", "status_code", "title", "meta_description", "canonical_url", "word_count", "content_type"))
    assert rows[1][0:5] == ["page-1", "https://example.com/", "https://example.com/", "200", "Home"]


def test_csv_exporter_writes_issues_with_stable_headers(tmp_path):
    path = tmp_path / "issues.csv"
    adapter = CsvExportAdapter(_id(CrawlId, "crawl-1"))
    row = IssueRow(
        _id(IssueId, "issue-1"),
        _url("https://example.com/missing"),
        IssueType.TITLE_MISSING,
        IssueSeverity.MEDIUM,
        "Missing title",
        _id(PageId, "page-1"),
    )

    result = adapter.write_issues(path, (row,))

    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert result.kind == ExportKind.ISSUES
    assert result.row_count == 1
    assert rows == [
        {
            "issue_id": "issue-1",
            "affected_url": "https://example.com/missing",
            "issue_type": "title_missing",
            "severity": "medium",
            "explanation": "Missing title",
            "page_id": "page-1",
        }
    ]


def test_export_service_passes_crawl_id_to_csv_adapter(tmp_path):
    class ReadRepository:
        def list_pages_for_export(self, crawl_id):
            return ()

    adapter = CsvExportAdapter()
    service = ExportApplicationService(ReadRepository(), adapter)
    crawl_id = _id(CrawlId, "crawl-from-command")

    result = service.export(ExportCommand(crawl_id, ExportKind.PAGES, tmp_path / "pages.csv"))

    assert result.success
    assert result.value.export_result.crawl_id == crawl_id
