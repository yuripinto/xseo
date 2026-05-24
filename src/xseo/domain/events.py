"""Explicit immutable domain events."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from xseo.domain.entities import CrawlConfig
from xseo.domain.enums import FetchStatus, IssueSeverity, IssueType
from xseo.domain.errors import DomainError
from xseo.domain.ids import CrawlId, DuplicateGroupId, IssueId, PageId
from xseo.domain.urls import NormalizedUrl
from xseo.domain.value_objects import ContentHash


@dataclass(frozen=True)
class DomainEvent:
    crawl_id: CrawlId
    occurred_at: datetime


@dataclass(frozen=True)
class CrawlStarted(DomainEvent):
    config: CrawlConfig


@dataclass(frozen=True)
class UrlQueued(DomainEvent):
    url: NormalizedUrl


@dataclass(frozen=True)
class PageFetched(DomainEvent):
    url: NormalizedUrl
    status: FetchStatus
    status_code: int | None = None


@dataclass(frozen=True)
class PageExtracted(DomainEvent):
    page_id: PageId
    url: NormalizedUrl


@dataclass(frozen=True)
class IssueFound(DomainEvent):
    issue_id: IssueId
    issue_type: IssueType
    severity: IssueSeverity


@dataclass(frozen=True)
class DuplicateGroupFound(DomainEvent):
    duplicate_group_id: DuplicateGroupId
    content_hash: ContentHash


@dataclass(frozen=True)
class CrawlProgressed(DomainEvent):
    pages_crawled: int
    queued_count: int
    issue_count: int
    error_count: int


@dataclass(frozen=True)
class CrawlStopped(DomainEvent):
    pages_crawled: int
    issue_count: int


@dataclass(frozen=True)
class CrawlCompleted(DomainEvent):
    pages_crawled: int
    issue_count: int
    duplicate_group_count: int


@dataclass(frozen=True)
class CrawlFailed(DomainEvent):
    error: DomainError
