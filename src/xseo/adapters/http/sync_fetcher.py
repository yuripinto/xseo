"""Synchronous HTTP fetch adapter for background thread use."""

from __future__ import annotations

import asyncio

import httpx

from xseo.adapters.http.httpx_fetcher import DEFAULT_MAX_BODY_BYTES, HttpxFetchAdapter


class SyncHttpFetchAdapter:
    """Wraps HttpxFetchAdapter for synchronous callers via asyncio.run().

    Safe to instantiate per-crawl inside a background thread.
    """

    def __init__(self, max_body_bytes: int = DEFAULT_MAX_BODY_BYTES) -> None:
        self.max_body_bytes = max_body_bytes

    def fetch(self, url: object, crawl_id: object = None) -> object:
        return asyncio.run(self._fetch_async(url, crawl_id))

    async def _fetch_async(self, url: object, crawl_id: object) -> object:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            return await HttpxFetchAdapter(client, self.max_body_bytes).fetch(
                url, crawl_id=crawl_id
            )
