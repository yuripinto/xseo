from xseo.domain.entities import FetchResult
from xseo.domain.enums import FetchStatus
from xseo.domain.frontier import FrontierAddStatus, RejectionReason, UrlFrontier
from xseo.domain.urls import NormalizedUrl


def _url(value):
    return NormalizedUrl.create(value).value


def test_frontier_accepts_and_dequeues_urls_fifo():
    frontier = UrlFrontier(_url("https://example.com/"))
    first = _url("https://example.com/a")
    second = _url("https://example.com/b")

    frontier.add(first, depth=1)
    frontier.add(second, depth=1)

    assert frontier.next_url().url == first
    assert frontier.next_url().url == second


def test_frontier_rejects_duplicate_urls():
    frontier = UrlFrontier(_url("https://example.com/"))
    target = _url("https://example.com/a")

    assert frontier.add(target, depth=1).status == FrontierAddStatus.ADDED
    duplicate = frontier.add(target, depth=1)

    assert duplicate.status == FrontierAddStatus.DUPLICATE
    assert duplicate.reason == RejectionReason.DUPLICATE


def test_frontier_rejects_off_host_urls():
    frontier = UrlFrontier(_url("https://example.com/"))

    result = frontier.add(_url("https://blog.example.com/a"), depth=1)

    assert result.status == FrontierAddStatus.OFF_HOST
    assert frontier.snapshot().rejected_count == 1


def test_frontier_counts_successful_pages_only():
    frontier = UrlFrontier(_url("https://example.com/"))
    success_url = _url("https://example.com/a")
    failed_url = _url("https://example.com/b")
    frontier.add(success_url, depth=1)
    frontier.add(failed_url, depth=1)

    frontier.mark_visited(
        success_url,
        FetchResult(success_url, success_url, FetchStatus.SUCCESS, content_type="text/html"),
    )
    frontier.mark_failed(
        failed_url,
        FetchResult(failed_url, None, FetchStatus.NETWORK_ERROR),
    )

    snapshot = frontier.snapshot()
    assert snapshot.successful_page_count == 1
    assert snapshot.failed_count == 1
