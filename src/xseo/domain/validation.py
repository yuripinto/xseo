"""Validation result primitives for expected domain validation failures."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

from xseo.domain.errors import DomainError

T = TypeVar("T")


@dataclass(frozen=True)
class DomainValidationError:
    code: object
    message: str

    @classmethod
    def of(cls, code: object, message: str) -> "DomainValidationError":
        return cls(code=code, message=message)


@dataclass(frozen=True)
class ValidationResult(Generic[T]):
    ok: bool
    value: T | None = None
    errors: tuple[DomainValidationError, ...] = ()

    @classmethod
    def success(cls, value: T) -> "ValidationResult[T]":
        return cls(ok=True, value=value, errors=())

    @classmethod
    def failure(
        cls, *errors: DomainValidationError | DomainError
    ) -> "ValidationResult[T]":
        converted = tuple(
            error
            if isinstance(error, DomainValidationError)
            else DomainValidationError.of(error.code, error.message)
            for error in errors
        )
        return cls(ok=False, value=None, errors=converted)

    @property
    def first_error(self) -> DomainValidationError | None:
        return self.errors[0] if self.errors else None
