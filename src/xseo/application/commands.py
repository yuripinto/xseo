"""Application command and query objects."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from xseo.domain.enums import ExportKind


@dataclass(frozen=True)
class StartCrawlCommand:
    start_url: str
    same_host_only: bool = True
    page_limit: int = 1000
    timeout_seconds: int = 10


@dataclass(frozen=True)
class StopCrawlCommand:
    crawl_id: object


@dataclass(frozen=True)
class QueryOptions:
    filters: dict[str, object] | None = None
    sort_field: str | None = None
    sort_direction: str = "asc"
    page_size: int | None = None
    offset: int = 0


@dataclass(frozen=True)
class ResultQuery:
    crawl_id: object
    options: QueryOptions = QueryOptions()


@dataclass(frozen=True)
class PageDetailQuery:
    crawl_id: object
    page_id: object


@dataclass(frozen=True)
class ExportCommand:
    crawl_id: object
    kind: ExportKind
    target_path: Path | str
