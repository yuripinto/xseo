from xseo.application.results import ApplicationResult, ExportStatus
from xseo.domain.enums import CrawlStatus, ExportKind
from xseo.domain.ids import CrawlId
from xseo.ui import XseoDesktopController


def _crawl_id(value="crawl-1"):
    return CrawlId.create(value).value


class CrawlService:
    def __init__(self):
        self.started = []
        self.stopped = []

    def start_crawl(self, command):
        self.started.append(command)
        return ApplicationResult.ok(
            type(
                "Session", (), {"crawl_id": _crawl_id(), "status": CrawlStatus.CREATED}
            )()
        )

    def request_stop(self, command):
        self.stopped.append(command)
        return ApplicationResult.ok(
            type("Active", (), {"status": CrawlStatus.STOPPING})()
        )


class ResultsService:
    def list_pages(self, query):
        return ApplicationResult.ok(("page",))

    def list_issues(self, query):
        return ApplicationResult.ok(("issue",))

    def list_duplicate_groups(self, query):
        return ApplicationResult.ok(("group",))


class ExportService:
    def __init__(self):
        self.commands = []

    def export(self, command):
        self.commands.append(command)
        return ApplicationResult.ok(ExportStatus(True, row_count=1))


def test_desktop_controller_start_refresh_stop_and_export(tmp_path):
    crawl_service = CrawlService()
    export_service = ExportService()
    controller = XseoDesktopController(crawl_service, ResultsService(), export_service)

    start = controller.start_crawl("https://example.com/")
    state = controller.refresh_results()
    stop = controller.stop_crawl()
    export = controller.export_pages(tmp_path / "pages.csv")

    assert start.success
    assert stop.success
    assert export.success
    assert state.pages == ("page",)
    assert state.issues == ("issue",)
    assert state.duplicate_groups == ("group",)
    assert export_service.commands[0].kind == ExportKind.PAGES
