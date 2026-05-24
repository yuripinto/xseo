"""URL value objects with structural validation."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from xseo.domain.errors import UrlErrorCode
from xseo.domain.validation import DomainValidationError, ValidationResult

_CRAWLABLE_SCHEMES = {"http", "https"}


def _url_error(code: UrlErrorCode, message: str) -> DomainValidationError:
    return DomainValidationError.of(code, message)


@dataclass(frozen=True)
class RawUrl:
    value: str

    @classmethod
    def create(cls, value: str) -> ValidationResult["RawUrl"]:
        if not isinstance(value, str) or not value.strip():
            return ValidationResult.failure(_url_error(UrlErrorCode.EMPTY, "URL is empty"))
        parsed = urlparse(value.strip())
        if parsed.scheme and parsed.scheme not in _CRAWLABLE_SCHEMES:
            return ValidationResult.failure(
                _url_error(UrlErrorCode.UNSUPPORTED_SCHEME, "URL scheme is unsupported")
            )
        return ValidationResult.success(cls(value.strip()))


@dataclass(frozen=True)
class BaseUrl:
    value: str

    @classmethod
    def create(cls, value: str) -> ValidationResult["BaseUrl"]:
        return _absolute_url(cls, value)


@dataclass(frozen=True)
class NormalizedUrl:
    value: str

    @classmethod
    def create(cls, value: str) -> ValidationResult["NormalizedUrl"]:
        return _absolute_url(cls, value)


def _absolute_url(cls, value: str):
    if not isinstance(value, str) or not value.strip():
        return ValidationResult.failure(_url_error(UrlErrorCode.EMPTY, "URL is empty"))

    parsed = urlparse(value.strip())
    if not parsed.scheme:
        return ValidationResult.failure(_url_error(UrlErrorCode.INVALID, "URL has no scheme"))
    if parsed.scheme not in _CRAWLABLE_SCHEMES:
        return ValidationResult.failure(
            _url_error(UrlErrorCode.UNSUPPORTED_SCHEME, "URL scheme is unsupported")
        )
    if not parsed.netloc:
        return ValidationResult.failure(_url_error(UrlErrorCode.MISSING_HOST, "URL has no host"))
    return ValidationResult.success(cls(value.strip()))
