"""Small domain value objects."""

from __future__ import annotations

from dataclasses import dataclass

from xseo.domain.errors import ExportErrorCode
from xseo.domain.validation import DomainValidationError, ValidationResult


@dataclass(frozen=True)
class ContentHash:
    value: str

    @classmethod
    def create(cls, value: str) -> ValidationResult["ContentHash"]:
        if not isinstance(value, str) or not value.strip():
            return ValidationResult.failure(
                DomainValidationError.of(
                    "content_hash.empty", "Content hash must be non-empty"
                )
            )
        return ValidationResult.success(cls(value.strip()))


@dataclass(frozen=True)
class WordCount:
    value: int

    @classmethod
    def create(cls, value: int) -> ValidationResult["WordCount"]:
        if not isinstance(value, int) or value < 0:
            return ValidationResult.failure(
                DomainValidationError.of(
                    "word_count.invalid", "Word count must be non-negative"
                )
            )
        return ValidationResult.success(cls(value))


@dataclass(frozen=True)
class FilePath:
    value: str

    @classmethod
    def create(cls, value: str) -> ValidationResult["FilePath"]:
        if not isinstance(value, str) or not value.strip():
            return ValidationResult.failure(
                DomainValidationError.of(
                    ExportErrorCode.INVALID_ROW_COUNT, "Path must be non-empty"
                )
            )
        return ValidationResult.success(cls(value.strip()))
