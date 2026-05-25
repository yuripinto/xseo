"""Hexagonal port contracts for domain boundaries."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Protocol

from xseo.domain.entities import (
    Crawl,
    DuplicateGroup,
    ExportResult,
    ExtractedPage,
    FetchResult,
    Heading,
    Issue,
    PageLink,
    Redirect,
)
from xseo.domain.events import DomainEvent
from xseo.domain.ids import CrawlId, PageId
from xseo.domain.urls import NormalizedUrl


class CrawlRepositoryPort(Protocol):
    def save_crawl(self, crawl: Crawl) -> CrawlId: ...
    def update_crawl(self, crawl: Crawl) -> None: ...
    def find_recent_crawl(self) -> Crawl | None: ...


class PageRepositoryPort(Protocol):
    def save_page(self, page: ExtractedPage) -> PageId: ...
    def save_links(self, page_id: PageId, links: tuple[PageLink, ...]) -> None: ...
    def save_headings(self, page_id: PageId, headings: tuple[Heading, ...]) -> None: ...
    def save_redirect(self, redirect: Redirect) -> None: ...


class IssueRepositoryPort(Protocol):
    def save_issues(self, crawl_id: CrawlId, issues: tuple[Issue, ...]) -> None: ...


class DuplicateRepositoryPort(Protocol):
    def save_duplicate_groups(
        self, crawl_id: CrawlId, groups: tuple[DuplicateGroup, ...]
    ) -> None: ...


class ExportRepositoryPort(Protocol):
    def save_export(self, export_result: ExportResult) -> None: ...


class HttpFetchPort(Protocol):
    def fetch(self, url: NormalizedUrl) -> FetchResult: ...


class RobotsPolicyPort(Protocol):
    def is_allowed(self, url: NormalizedUrl) -> bool: ...


class CsvExportPort(Protocol):
    def write_pages(self, path: Path, rows: tuple[object, ...]) -> ExportResult: ...
    def write_issues(self, path: Path, rows: tuple[object, ...]) -> ExportResult: ...


class EventPublisherPort(Protocol):
    def publish(self, event: DomainEvent) -> None: ...


class EventSinkPort(Protocol):
    def emit(self, event: DomainEvent) -> None: ...


class ClockPort(Protocol):
    def now(self) -> datetime: ...
