"""UI-facing read models for application services."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class CrawlSession:
    crawl_id: object
    status: object
    created_at: datetime | None = None
    started_at: datetime | None = None


@dataclass(frozen=True)
class CrawlProgressStatus:
    crawl_id: object
    status: object
    pages_crawled: int = 0
    queued_urls: int | None = None
    error_count: int = 0
    issue_count: int = 0
    duplicate_group_count: int = 0
    current_url: object | None = None
    message: str | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


@dataclass(frozen=True)
class PageRow:
    page_id: object
    url: object
    final_url: object
    status_code: int
    title: str | None
    meta_description: str | None
    canonical_url: object | None
    word_count: int
    content_type: str | None = None


@dataclass(frozen=True)
class IssueRow:
    issue_id: object
    affected_url: object
    issue_type: object
    severity: object
    explanation: str
    page_id: object | None = None


@dataclass(frozen=True)
class DuplicateGroupRow:
    duplicate_group_id: object
    content_hash: object
    page_count: int
    representative_url: object | None = None


@dataclass(frozen=True)
class PageDetail:
    page: PageRow
    headings: tuple[object, ...] = ()
    outlinks: tuple[object, ...] = ()
    redirects: tuple[object, ...] = ()
    content_hash: object | None = None
    issues: tuple[IssueRow, ...] = ()
