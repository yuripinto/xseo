"""Async httpx fetch adapter."""

from __future__ import annotations

from typing import Protocol

import httpx

from xseo.domain.entities import FetchResult, Redirect
from xseo.domain.enums import FetchStatus
from xseo.domain.errors import DomainError
from xseo.domain.frontier import UrlNormalizer
from xseo.domain.ids import CrawlId
from xseo.domain.urls import NormalizedUrl

DEFAULT_MAX_BODY_BYTES = 5 * 1024 * 1024


class AsyncHttpFetchPort(Protocol):
    async def fetch(
        self,
        url: NormalizedUrl,
        timeout_seconds: int = 10,
        crawl_id: CrawlId | None = None,
    ) -> FetchResult: ...


class HttpxFetchAdapter:
    def __init__(self, client: httpx.AsyncClient | None = None, max_body_bytes: int = DEFAULT_MAX_BODY_BYTES):
        self.client = client
        self.max_body_bytes = max_body_bytes
        self.normalizer = UrlNormalizer()

    async def fetch(self, url: NormalizedUrl, timeout_seconds: int = 10, crawl_id: CrawlId | None = None):
        try:
            if self.client is None:
                async with httpx.AsyncClient(follow_redirects=True) as client:
                    response = await client.get(url.value, timeout=timeout_seconds)
            else:
                response = await self.client.get(
                    url.value,
                    timeout=timeout_seconds,
                    follow_redirects=True,
                )
            return self._to_fetch_result(url, response, crawl_id)
        except httpx.TimeoutException as exc:
            return _failure(url, FetchStatus.TIMEOUT, "fetch.timeout", str(exc))
        except httpx.NetworkError as exc:
            return _failure(url, FetchStatus.NETWORK_ERROR, "fetch.network_error", str(exc))
        except httpx.HTTPError as exc:
            return _failure(url, FetchStatus.INVALID_RESPONSE, "fetch.invalid_response", str(exc))

    def _to_fetch_result(self, requested_url, response, crawl_id):
        body = response.content
        if len(body) > self.max_body_bytes:
            return FetchResult(
                requested_url=requested_url,
                final_url=self._normalize_response_url(response.url),
                status=FetchStatus.UNSUPPORTED_CONTENT,
                status_code=response.status_code,
                content_type=response.headers.get("content-type"),
                body=None,
                redirect_chain=self._redirect_chain(response, crawl_id),
                error=DomainError.of("fetch.unsupported_content", "Response body exceeds retained size limit"),
            )

        final_url = self._normalize_response_url(response.url)
        if final_url is None:
            return _failure(
                requested_url,
                FetchStatus.INVALID_RESPONSE,
                "fetch.invalid_final_url",
                "Final response URL could not be normalized",
            )

        return FetchResult(
            requested_url=requested_url,
            final_url=final_url,
            status=FetchStatus.SUCCESS,
            status_code=response.status_code,
            content_type=response.headers.get("content-type"),
            body=body,
            redirect_chain=self._redirect_chain(response, crawl_id),
        )

    def _normalize_response_url(self, url):
        result = self.normalizer.normalize(str(url))
        return result.value if result.ok else None

    def _redirect_chain(self, response, crawl_id):
        if crawl_id is None:
            return ()
        hops = []
        responses = list(response.history) + [response]
        for index, history_response in enumerate(response.history):
            from_url = self._normalize_response_url(history_response.request.url)
            to_url = self._normalize_response_url(responses[index + 1].url)
            if from_url is None or to_url is None:
                continue
            hops.append(
                Redirect(
                    crawl_id=crawl_id,
                    from_url=from_url,
                    to_url=to_url,
                    status_code=history_response.status_code,
                )
            )
        return tuple(hops)


def _failure(url, status, code, message):
    return FetchResult(
        requested_url=url,
        final_url=None,
        status=status,
        error=DomainError.of(code, message),
    )
