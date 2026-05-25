import asyncio

import httpx

from xseo.adapters.http import HttpxFetchAdapter
from xseo.domain.enums import FetchStatus
from xseo.domain.ids import CrawlId
from xseo.domain.urls import NormalizedUrl


def _url(value="https://example.com/"):
    return NormalizedUrl.create(value).value


def test_httpx_fetcher_converts_successful_response():
    async def run():
        transport = httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                headers={"content-type": "text/html"},
                content=b"<html><title>OK</title></html>",
                request=request,
            )
        )
        async with httpx.AsyncClient(transport=transport) as client:
            return await HttpxFetchAdapter(client).fetch(_url())

    result = asyncio.run(run())

    assert result.status == FetchStatus.SUCCESS
    assert result.final_url.value == "https://example.com/"
    assert result.body == b"<html><title>OK</title></html>"


def test_httpx_fetcher_rejects_oversized_body():
    async def run():
        transport = httpx.MockTransport(
            lambda request: httpx.Response(200, content=b"abcdef", request=request)
        )
        async with httpx.AsyncClient(transport=transport) as client:
            return await HttpxFetchAdapter(client, max_body_bytes=3).fetch(_url())

    result = asyncio.run(run())

    assert result.status == FetchStatus.UNSUPPORTED_CONTENT
    assert result.body is None
    assert result.error.code == "fetch.unsupported_content"


def test_httpx_fetcher_converts_timeout_exception():
    async def run():
        def handler(request):
            raise httpx.ReadTimeout("timeout", request=request)

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            return await HttpxFetchAdapter(client).fetch(_url())

    result = asyncio.run(run())

    assert result.status == FetchStatus.TIMEOUT
    assert result.error.code == "fetch.timeout"


def test_httpx_fetcher_records_redirect_chain_when_crawl_id_is_available():
    async def run():
        def handler(request):
            if str(request.url) == "https://example.com/":
                return httpx.Response(
                    301,
                    headers={"location": "https://example.com/final"},
                    request=request,
                )
            return httpx.Response(200, content=b"ok", request=request)

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(
            transport=transport, follow_redirects=True
        ) as client:
            return await HttpxFetchAdapter(client).fetch(
                _url(),
                crawl_id=CrawlId.create("crawl-1").value,
            )

    result = asyncio.run(run())

    assert result.status == FetchStatus.SUCCESS
    assert result.final_url.value == "https://example.com/final"
    assert len(result.redirect_chain) == 1
    assert result.redirect_chain[0].status_code == 301
