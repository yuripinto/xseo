from pathlib import Path

from xseo.application import ExportCommand
from xseo.application.services import ExportApplicationService
from xseo.domain.entities import ExportResult
from xseo.domain.enums import ExportKind
from xseo.domain.ids import CrawlId, ExportId
from xseo.domain.value_objects import FilePath


def _id(cls, value):
    return cls.create(value).value


class ReadRepository:
    def list_pages_for_export(self, crawl_id):
        return ("page-row",)

    def list_issues_for_export(self, crawl_id):
        return ("issue-row-1", "issue-row-2")


class ExportPort:
    def __init__(self):
        self.calls = []

    def write_pages(self, target_path, rows):
        self.calls.append(("pages", target_path, rows))
        return _export_result(ExportKind.PAGES, target_path, len(rows))

    def write_issues(self, target_path, rows):
        self.calls.append(("issues", target_path, rows))
        return _export_result(ExportKind.ISSUES, target_path, len(rows))


class ExportRepository:
    def __init__(self):
        self.saved = []

    def save_export(self, export_result):
        self.saved.append(export_result)


def _export_result(kind, target_path, row_count):
    return ExportResult.create(
        _id(ExportId, f"export-{kind.value}"),
        _id(CrawlId, "crawl-1"),
        kind,
        FilePath.create(str(target_path)).value,
        row_count,
        True,
    ).value


def test_export_service_calls_export_port_and_saves_metadata():
    export_port = ExportPort()
    export_repository = ExportRepository()
    service = ExportApplicationService(ReadRepository(), export_port, export_repository)
    command = ExportCommand(
        _id(CrawlId, "crawl-1"), ExportKind.ISSUES, Path("issues.csv")
    )

    result = service.export(command)

    assert result.success
    assert result.value.row_count == 2
    assert export_port.calls[0][0] == "issues"
    assert len(export_repository.saved) == 1
