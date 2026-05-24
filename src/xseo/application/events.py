"""Application-level crawl progress events."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class CrawlProgressEventKind(StrEnum):
    CRAWL_STARTED = "crawl_started"
    URL_QUEUED = "url_queued"
    PAGE_FETCHED = "page_fetched"
    PAGE_EXTRACTED = "page_extracted"
    ISSUE_ANALYSIS_COMPLETED = "issue_analysis_completed"
    DUPLICATE_ANALYSIS_COMPLETED = "duplicate_analysis_completed"
    CRAWL_STOPPED = "crawl_stopped"
    CRAWL_COMPLETED = "crawl_completed"
    CRAWL_FAILED = "crawl_failed"
    STATUS_CHANGED = "status_changed"


@dataclass(frozen=True)
class CrawlProgressEvent:
    crawl_id: object
    kind: CrawlProgressEventKind
    status: object
    occurred_at: datetime
    message: str | None = None
