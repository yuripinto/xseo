"""Core domain entities and aggregate state transitions."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime

from xseo.domain.enums import (
    CrawlStatus,
    ExportKind,
    FetchStatus,
    HeadingLevel,
    IssueSeverity,
    IssueType,
    LinkRelation,
)
from xseo.domain.errors import CrawlConfigErrorCode, CrawlStateErrorCode, DomainError
from xseo.domain.ids import CrawlId, DuplicateGroupId, ExportId, IssueId, PageId
from xseo.domain.urls import BaseUrl, NormalizedUrl
from xseo.domain.validation import DomainValidationError, ValidationResult
from xseo.domain.value_objects import ContentHash, FilePath, WordCount


@dataclass(frozen=True)
class CrawlConfig:
    start_url: BaseUrl
    same_host_only: bool = True
    page_limit: int = 1000
    timeout_seconds: int = 10
    request_delay_seconds: float = 0.5
    respect_robots: bool = True

    @classmethod
    def create(
        cls,
        start_url: BaseUrl,
        same_host_only: bool = True,
        page_limit: int = 1000,
        timeout_seconds: int = 10,
        request_delay_seconds: float = 0.5,
        respect_robots: bool = True,
    ) -> ValidationResult["CrawlConfig"]:
        errors = []
        if page_limit <= 0:
            errors.append(
                DomainValidationError.of(
                    CrawlConfigErrorCode.INVALID_PAGE_LIMIT,
                    "Page limit must be positive",
                )
            )
        if timeout_seconds <= 0:
            errors.append(
                DomainValidationError.of(
                    CrawlConfigErrorCode.INVALID_TIMEOUT,
                    "Timeout must be positive",
                )
            )
        if request_delay_seconds < 0:
            errors.append(
                DomainValidationError.of(
                    CrawlConfigErrorCode.INVALID_REQUEST_DELAY,
                    "Request delay must be non-negative",
                )
            )
        if errors:
            return ValidationResult.failure(*errors)
        return ValidationResult.success(
            cls(
                start_url=start_url,
                same_host_only=same_host_only,
                page_limit=page_limit,
                timeout_seconds=timeout_seconds,
                request_delay_seconds=request_delay_seconds,
                respect_robots=respect_robots,
            )
        )


@dataclass(frozen=True)
class Crawl:
    crawl_id: CrawlId
    config: CrawlConfig
    status: CrawlStatus
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    failure: DomainError | None = None

    @classmethod
    def create(cls, crawl_id: CrawlId, config: CrawlConfig, now: datetime) -> "Crawl":
        return cls(
            crawl_id=crawl_id,
            config=config,
            status=CrawlStatus.CREATED,
            created_at=now,
        )

    def start(self, now: datetime) -> ValidationResult["Crawl"]:
        if self.status != CrawlStatus.CREATED:
            return _invalid_transition(self.status, CrawlStatus.RUNNING)
        return ValidationResult.success(
            replace(self, status=CrawlStatus.RUNNING, started_at=now)
        )

    def request_stop(self, now: datetime) -> ValidationResult["Crawl"]:
        if self.status != CrawlStatus.RUNNING:
            return _invalid_transition(self.status, CrawlStatus.STOPPING)
        return ValidationResult.success(replace(self, status=CrawlStatus.STOPPING))

    def mark_stopped(self, now: datetime) -> ValidationResult["Crawl"]:
        if self.status != CrawlStatus.STOPPING:
            return _invalid_transition(self.status, CrawlStatus.STOPPED)
        return ValidationResult.success(
            replace(self, status=CrawlStatus.STOPPED, completed_at=now)
        )

    def complete(self, now: datetime) -> ValidationResult["Crawl"]:
        if self.status != CrawlStatus.RUNNING:
            return _invalid_transition(self.status, CrawlStatus.COMPLETED)
        return ValidationResult.success(
            replace(self, status=CrawlStatus.COMPLETED, completed_at=now)
        )

    def fail(self, error: DomainError, now: datetime) -> ValidationResult["Crawl"]:
        if self.status not in {CrawlStatus.RUNNING, CrawlStatus.STOPPING}:
            return _invalid_transition(self.status, CrawlStatus.FAILED)
        return ValidationResult.success(
            replace(self, status=CrawlStatus.FAILED, completed_at=now, failure=error)
        )


def _invalid_transition(
    current: CrawlStatus, target: CrawlStatus
) -> ValidationResult[Crawl]:
    return ValidationResult.failure(
        DomainValidationError.of(
            CrawlStateErrorCode.INVALID_TRANSITION,
            f"Cannot transition crawl from {current.value} to {target.value}",
        )
    )


@dataclass(frozen=True)
class UrlRecord:
    url: NormalizedUrl
    depth: int
    source_page_id: PageId | None = None


@dataclass(frozen=True)
class Redirect:
    crawl_id: CrawlId
    from_url: NormalizedUrl
    to_url: NormalizedUrl
    status_code: int


@dataclass(frozen=True)
class FetchResult:
    requested_url: NormalizedUrl
    final_url: NormalizedUrl | None
    status: FetchStatus
    status_code: int | None = None
    content_type: str | None = None
    body: bytes | None = None
    redirect_chain: tuple[Redirect, ...] = ()
    error: DomainError | None = None


@dataclass(frozen=True)
class ExtractedPage:
    page_id: PageId
    crawl_id: CrawlId
    url: NormalizedUrl
    final_url: NormalizedUrl
    status_code: int
    content_type: str | None
    title: str | None
    meta_description: str | None
    canonical_url: NormalizedUrl | None
    robots_meta: str | None
    word_count: WordCount
    content_length: int
    content_hash: ContentHash | None
    image_count: int = 0
    images_missing_alt: int = 0


@dataclass(frozen=True)
class PageLink:
    source_page_id: PageId
    target_url: NormalizedUrl
    relation: LinkRelation
    anchor_text: str
    nofollow: bool = False


@dataclass(frozen=True)
class Heading:
    page_id: PageId
    level: HeadingLevel
    text: str
    position: int


@dataclass(frozen=True)
class ExtractionResult:
    page: ExtractedPage | None
    links: tuple[PageLink, ...] = ()
    headings: tuple[Heading, ...] = ()
    error: DomainError | None = None


@dataclass(frozen=True)
class Issue:
    issue_id: IssueId
    crawl_id: CrawlId
    page_id: PageId | None
    affected_url: NormalizedUrl
    issue_type: IssueType
    severity: IssueSeverity
    explanation: str


@dataclass(frozen=True)
class DuplicateGroup:
    duplicate_group_id: DuplicateGroupId
    crawl_id: CrawlId
    content_hash: ContentHash
    page_ids: tuple[PageId, ...]

    @classmethod
    def create(
        cls,
        duplicate_group_id: DuplicateGroupId,
        crawl_id: CrawlId,
        content_hash: ContentHash,
        page_ids: tuple[PageId, ...],
    ) -> ValidationResult["DuplicateGroup"]:
        if len(page_ids) < 2:
            return ValidationResult.failure(
                DomainValidationError.of(
                    "duplicate_group.too_small",
                    "Duplicate group must contain at least two pages",
                )
            )
        return ValidationResult.success(
            cls(
                duplicate_group_id=duplicate_group_id,
                crawl_id=crawl_id,
                content_hash=content_hash,
                page_ids=page_ids,
            )
        )


@dataclass(frozen=True)
class ExportResult:
    export_id: ExportId
    crawl_id: CrawlId
    kind: ExportKind
    target_path: FilePath
    row_count: int
    success: bool
    error: DomainError | None = None

    @classmethod
    def create(
        cls,
        export_id: ExportId,
        crawl_id: CrawlId,
        kind: ExportKind,
        target_path: FilePath,
        row_count: int,
        success: bool,
        error: DomainError | None = None,
    ) -> ValidationResult["ExportResult"]:
        if row_count < 0:
            return ValidationResult.failure(
                DomainValidationError.of(
                    "export.invalid_row_count",
                    "Export row count must be non-negative",
                )
            )
        return ValidationResult.success(
            cls(
                export_id=export_id,
                crawl_id=crawl_id,
                kind=kind,
                target_path=target_path,
                row_count=row_count,
                success=success,
                error=error,
            )
        )
