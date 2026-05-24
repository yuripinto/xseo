"""URL normalization for crawl frontier identity."""

from __future__ import annotations

from urllib.parse import urljoin, urlparse, urlunparse

from xseo.domain.errors import UrlErrorCode
from xseo.domain.urls import BaseUrl, NormalizedUrl, RawUrl
from xseo.domain.validation import DomainValidationError, ValidationResult

_CRAWLABLE_SCHEMES = {"http", "https"}


class UrlNormalizer:
    def normalize(self, raw_url, base_url=None):
        raw_value = _url_value(raw_url)
        if not isinstance(raw_value, str) or not raw_value.strip():
            return _failure(UrlErrorCode.EMPTY, "URL is empty")

        candidate = raw_value.strip()
        if base_url is not None:
            candidate = urljoin(_url_value(base_url), candidate)

        try:
            parsed = urlparse(candidate)
            scheme = parsed.scheme.lower()
            host = parsed.hostname.lower() if parsed.hostname else ""
            port = parsed.port
        except ValueError:
            return _failure(UrlErrorCode.INVALID, "URL is invalid")

        if not scheme:
            return _failure(UrlErrorCode.INVALID, "URL has no scheme")
        if scheme not in _CRAWLABLE_SCHEMES:
            return _failure(UrlErrorCode.UNSUPPORTED_SCHEME, "URL scheme is unsupported")
        if not host:
            return _failure(UrlErrorCode.MISSING_HOST, "URL has no host")

        netloc = host
        if port is not None and not _is_default_port(scheme, port):
            netloc = f"{host}:{port}"

        normalized = urlunparse(
            (scheme, netloc, parsed.path, parsed.params, parsed.query, "")
        )
        return NormalizedUrl.create(normalized)

    def normalize_discovered(self, candidate_url, source_url):
        return self.normalize(candidate_url, base_url=source_url)


def _url_value(url):
    if isinstance(url, (RawUrl, BaseUrl, NormalizedUrl)):
        return url.value
    return url


def _is_default_port(scheme, port):
    return (scheme == "http" and port == 80) or (scheme == "https" and port == 443)


def _failure(code, message):
    return ValidationResult.failure(DomainValidationError.of(code, message))
