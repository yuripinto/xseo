"""Export application service."""

from __future__ import annotations

from pathlib import Path

from xseo.application.results import ApplicationResult, ExportStatus
from xseo.domain.enums import ExportKind


class ExportApplicationService:
    def __init__(self, read_repository, export_port, export_repository=None):
        self.read_repository = read_repository
        self.export_port = export_port
        self.export_repository = export_repository

    def export_pages(self, command):
        rows = tuple(self.read_repository.list_pages_for_export(command.crawl_id))
        return self._write(command, rows, self.export_port.write_pages)

    def export_issues(self, command):
        rows = tuple(self.read_repository.list_issues_for_export(command.crawl_id))
        return self._write(command, rows, self.export_port.write_issues)

    def export(self, command):
        if command.kind == ExportKind.PAGES:
            return self.export_pages(command)
        if command.kind == ExportKind.ISSUES:
            return self.export_issues(command)
        return ApplicationResult.fail(
            "Export kind is not supported", "export.unsupported_kind"
        )

    def _write(self, command, rows, writer):
        try:
            if hasattr(self.export_port, "set_crawl_id"):
                self.export_port.set_crawl_id(command.crawl_id)
            export_result = writer(Path(command.target_path), rows)
            if self.export_repository is not None:
                self.export_repository.save_export(export_result)
            return ApplicationResult.ok(
                ExportStatus(
                    success=getattr(export_result, "success", True),
                    export_result=export_result,
                    row_count=getattr(export_result, "row_count", len(rows)),
                )
            )
        except Exception as exc:
            return ApplicationResult.fail(str(exc), "export.failed")
