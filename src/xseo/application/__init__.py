"""Application service layer for xseo."""

from xseo.application.commands import ExportCommand, PageDetailQuery, QueryOptions, ResultQuery, StartCrawlCommand, StopCrawlCommand
from xseo.application.events import CrawlProgressEvent, CrawlProgressEventKind
from xseo.application.query import apply_query_options, validate_query_options
from xseo.application.read_models import (
    CrawlProgressStatus,
    CrawlSession,
    DuplicateGroupRow,
    IssueRow,
    PageDetail,
    PageRow,
)
from xseo.application.results import ApplicationResult, ExportStatus
from xseo.application.services import (
    ActiveCrawl,
    ActiveCrawlRegistry,
    CrawlApplicationService,
    CrawlExecutionCoordinator,
    EventDeliveryService,
    ExportApplicationService,
    PublishResult,
    ResultsApplicationService,
    Subscription,
)

__all__ = [
    "ActiveCrawl",
    "ActiveCrawlRegistry",
    "ApplicationResult",
    "CrawlApplicationService",
    "CrawlExecutionCoordinator",
    "CrawlProgressEvent",
    "CrawlProgressEventKind",
    "CrawlProgressStatus",
    "CrawlSession",
    "DuplicateGroupRow",
    "EventDeliveryService",
    "ExportApplicationService",
    "ExportCommand",
    "ExportStatus",
    "IssueRow",
    "PageDetail",
    "PageDetailQuery",
    "PageRow",
    "PublishResult",
    "QueryOptions",
    "ResultQuery",
    "ResultsApplicationService",
    "StartCrawlCommand",
    "StopCrawlCommand",
    "Subscription",
    "apply_query_options",
    "validate_query_options",
]
