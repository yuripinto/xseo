"""robots.txt policy adapter.

Fetches and caches one ``robots.txt`` per host and answers allow/deny
questions for crawled URLs. Fetch failures and missing files fail open
(allow), matching common crawler convention; an explicit ``Disallow`` is
honored.
"""

from __future__ import annotations

from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx

DEFAULT_USER_AGENT = "xseo"


def httpx_robots_fetcher(timeout_seconds: int = 10):
    """Return a callable that fetches robots.txt text, or None on any failure."""

    def fetch_text(robots_url: str) -> str | None:
        try:
            response = httpx.get(
                robots_url, timeout=timeout_seconds, follow_redirects=True
            )
        except httpx.HTTPError:
            return None
        if response.status_code >= 400:
            return None
        return response.text

    return fetch_text


class RobotsTxtPolicy:
    """Per-host robots.txt allow/deny policy with caching."""

    def __init__(self, fetch_text, user_agent: str = DEFAULT_USER_AGENT) -> None:
        self._fetch_text = fetch_text
        self._user_agent = user_agent
        self._parsers: dict[tuple[str, str], RobotFileParser] = {}

    def is_allowed(self, url) -> bool:
        value = getattr(url, "value", url)
        parsed = urlparse(value)
        if not parsed.scheme or not parsed.netloc:
            return True
        key = (parsed.scheme, parsed.netloc)
        parser = self._parsers.get(key)
        if parser is None:
            parser = self._load(parsed.scheme, parsed.netloc)
            self._parsers[key] = parser
        return parser.can_fetch(self._user_agent, value)

    def _load(self, scheme: str, netloc: str) -> RobotFileParser:
        parser = RobotFileParser()
        text = self._fetch_text(f"{scheme}://{netloc}/robots.txt")
        if text is None:
            parser.allow_all = True
        else:
            parser.parse(text.splitlines())
        return parser


class AllowAllRobotsPolicy:
    """No-op policy used when robots.txt compliance is disabled."""

    def is_allowed(self, url) -> bool:  # noqa: ARG002
        return True
