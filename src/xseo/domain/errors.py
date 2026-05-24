"""Domain error codes and error values."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class IdErrorCode(StrEnum):
    EMPTY = "id.empty"


class UrlErrorCode(StrEnum):
    EMPTY = "url.empty"
    INVALID = "url.invalid"
    UNSUPPORTED_SCHEME = "url.unsupported_scheme"
    MISSING_HOST = "url.missing_host"


class CrawlConfigErrorCode(StrEnum):
    INVALID_PAGE_LIMIT = "crawl_config.invalid_page_limit"
    INVALID_TIMEOUT = "crawl_config.invalid_timeout"


class CrawlStateErrorCode(StrEnum):
    INVALID_TRANSITION = "crawl_state.invalid_transition"


class EventErrorCode(StrEnum):
    MISSING_PAYLOAD = "event.missing_payload"


class ExportErrorCode(StrEnum):
    INVALID_ROW_COUNT = "export.invalid_row_count"


@dataclass(frozen=True)
class DomainError:
    code: StrEnum | str
    message: str

    @classmethod
    def of(cls, code: StrEnum | str, message: str) -> "DomainError":
        return cls(code=code, message=message)
