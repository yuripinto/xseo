"""Typed immutable domain IDs."""

from __future__ import annotations

from dataclasses import dataclass

from xseo.domain.errors import IdErrorCode
from xseo.domain.validation import DomainValidationError, ValidationResult


@dataclass(frozen=True)
class _TypedId:
    value: str

    @classmethod
    def create(cls, value: str):
        if not isinstance(value, str) or not value.strip():
            return ValidationResult.failure(
                DomainValidationError.of(IdErrorCode.EMPTY, "ID must be non-empty")
            )
        return ValidationResult.success(cls(value.strip()))


@dataclass(frozen=True)
class CrawlId(_TypedId):
    pass


@dataclass(frozen=True)
class PageId(_TypedId):
    pass


@dataclass(frozen=True)
class IssueId(_TypedId):
    pass


@dataclass(frozen=True)
class DuplicateGroupId(_TypedId):
    pass


@dataclass(frozen=True)
class ExportId(_TypedId):
    pass
