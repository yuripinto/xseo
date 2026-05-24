"""Application service result objects."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ApplicationResult:
    success: bool
    value: object | None = None
    message: str | None = None
    error_code: str | None = None

    @classmethod
    def ok(cls, value=None, message=None):
        return cls(True, value=value, message=message)

    @classmethod
    def fail(cls, message, error_code=None, value=None):
        return cls(False, value=value, message=message, error_code=error_code)


@dataclass(frozen=True)
class ExportStatus:
    success: bool
    export_result: object | None = None
    row_count: int = 0
    message: str | None = None
    error_code: str | None = None
