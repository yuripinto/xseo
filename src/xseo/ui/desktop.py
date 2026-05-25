"""Desktop-facing controller and state model."""

from __future__ import annotations

from dataclasses import dataclass

from xseo.application.commands import (
    ExportCommand,
    ResultQuery,
    StartCrawlCommand,
    StopCrawlCommand,
)
from xseo.domain.enums import ExportKind


@dataclass(frozen=True)
class DesktopState:
    selected_crawl_id: object | None = None
    crawl_status: object | None = None
    pages: tuple = ()
    issues: tuple = ()
    duplicate_groups: tuple = ()
    busy: bool = False
    last_error: str | None = None
    export_status: object | None = None


class XseoDesktopController:
    def __init__(self, crawl_service, results_service, export_service=None, state=None):
        self.crawl_service = crawl_service
        self.results_service = results_service
        self.export_service = export_service
        self.state = state or DesktopState()

    def start_crawl(
        self,
        start_url,
        same_host_only=True,
        page_limit=1000,
        timeout_seconds=10,
        request_delay_seconds=0.5,
        respect_robots=True,
    ):
        self.state = _replace(self.state, busy=True, last_error=None)
        result = self.crawl_service.start_crawl(
            StartCrawlCommand(
                start_url,
                same_host_only,
                page_limit,
                timeout_seconds,
                request_delay_seconds,
                respect_robots,
            )
        )
        if not result.success:
            self.state = _replace(self.state, busy=False, last_error=result.message)
            return result
        session = result.value
        self.state = _replace(
            self.state,
            selected_crawl_id=session.crawl_id,
            crawl_status=session.status,
            busy=False,
            last_error=None,
        )
        return result

    def stop_crawl(self):
        if self.state.selected_crawl_id is None:
            self.state = _replace(self.state, last_error="No crawl selected")
            return None
        result = self.crawl_service.request_stop(
            StopCrawlCommand(self.state.selected_crawl_id)
        )
        if result.success:
            self.state = _replace(
                self.state,
                crawl_status=getattr(result.value, "status", self.state.crawl_status),
            )
        else:
            self.state = _replace(self.state, last_error=result.message)
        return result

    def refresh_results(self, crawl_id=None):
        selected = crawl_id or self.state.selected_crawl_id
        if selected is None:
            self.state = _replace(self.state, last_error="No crawl selected")
            return self.state
        pages = self.results_service.list_pages(ResultQuery(selected))
        issues = self.results_service.list_issues(ResultQuery(selected))
        groups = self.results_service.list_duplicate_groups(ResultQuery(selected))
        for result in (pages, issues, groups):
            if not result.success:
                self.state = _replace(self.state, last_error=result.message)
                return self.state
        self.state = _replace(
            self.state,
            selected_crawl_id=selected,
            pages=pages.value,
            issues=issues.value,
            duplicate_groups=groups.value,
            last_error=None,
        )
        return self.state

    def export_pages(self, target_path):
        return self._export(ExportKind.PAGES, target_path)

    def export_issues(self, target_path):
        return self._export(ExportKind.ISSUES, target_path)

    def _export(self, kind, target_path):
        if self.export_service is None:
            self.state = _replace(
                self.state, last_error="Export service is not configured"
            )
            return None
        if self.state.selected_crawl_id is None:
            self.state = _replace(self.state, last_error="No crawl selected")
            return None
        result = self.export_service.export(
            ExportCommand(self.state.selected_crawl_id, kind, target_path)
        )
        if result.success:
            self.state = _replace(
                self.state, export_status=result.value, last_error=None
            )
        else:
            self.state = _replace(self.state, last_error=result.message)
        return result


def _replace(state, **changes):
    values = {
        "selected_crawl_id": state.selected_crawl_id,
        "crawl_status": state.crawl_status,
        "pages": state.pages,
        "issues": state.issues,
        "duplicate_groups": state.duplicate_groups,
        "busy": state.busy,
        "last_error": state.last_error,
        "export_status": state.export_status,
    }
    values.update(changes)
    return DesktopState(**values)
