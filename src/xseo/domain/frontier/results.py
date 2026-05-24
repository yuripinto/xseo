"""Result objects for URL frontier operations."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from xseo.domain.urls import NormalizedUrl


class FrontierEntryState(StrEnum):
    QUEUED = "queued"
    VISITED = "visited"
    REJECTED = "rejected"
    FAILED = "failed"


class RejectionReason(StrEnum):
    INVALID_URL = "invalid_url"
    OFF_HOST = "off_host"
    DUPLICATE = "duplicate"
    DEPTH_LIMIT_EXCEEDED = "depth_limit_exceeded"


class FrontierAddStatus(StrEnum):
    ADDED = "added"
    DUPLICATE = "duplicate"
    INVALID = "invalid"
    OFF_HOST = "off_host"
    REJECTED = "rejected"


@dataclass(frozen=True)
class FrontierEntry:
    url: NormalizedUrl
    depth: int
    state: FrontierEntryState
    rejection_reason: RejectionReason | None = None
    failure_message: str | None = None


@dataclass(frozen=True)
class RejectedUrl:
    candidate_url: str
    reason: RejectionReason
    normalized_url: NormalizedUrl | None = None
    source_url: NormalizedUrl | None = None


@dataclass(frozen=True)
class FrontierAddResult:
    status: FrontierAddStatus
    url: NormalizedUrl | None = None
    reason: RejectionReason | None = None

    @property
    def added(self):
        return self.status == FrontierAddStatus.ADDED


@dataclass(frozen=True)
class FrontierAddSummary:
    added_count: int = 0
    duplicate_count: int = 0
    invalid_count: int = 0
    off_host_count: int = 0
    rejected_count: int = 0


@dataclass(frozen=True)
class FrontierSnapshot:
    queued_count: int
    visited_count: int
    rejected_count: int
    failed_count: int
    successful_page_count: int
    current_url: NormalizedUrl | None = None
    maximum_depth: int | None = None
