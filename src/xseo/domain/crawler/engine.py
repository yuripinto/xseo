"""Stop-aware domain crawl loop."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Protocol

from xseo.domain.crawler.stop import NeverStopToken
from xseo.domain.entities import Crawl, FetchResult
from xseo.domain.enums import CrawlStatus, FetchStatus
from xseo.domain.errors import DomainError
from xseo.domain.events import (
    CrawlCompleted,
    CrawlFailed,
    CrawlProgressed,
    CrawlStarted,
    CrawlStopped,
    PageFetched,
    UrlQueued,
)
from xseo.domain.frontier.frontier import UrlFrontier
from xseo.domain.frontier.normalization import UrlNormalizer
from xseo.domain.frontier.results import FrontierSnapshot


class LinkDiscoveryPort(Protocol):
    def discover_links(self, fetch_result: FetchResult): ...


@dataclass(frozen=True)
class CrawlRunResult:
    crawl: Crawl
    final_status: CrawlStatus
    snapshot: FrontierSnapshot
    successful_page_count: int
    attempted_fetch_count: int
    failure: DomainError | None = None


class UrlCrawlEngine:
    def __init__(
        self,
        fetch_port,
        event_publisher,
        clock,
        normalizer=None,
        link_discovery=None,
        robots_policy=None,
        request_delay_seconds=0.0,
        sleeper=None,
    ):
        self.fetch_port = fetch_port
        self.event_publisher = event_publisher
        self.clock = clock
        self.normalizer = normalizer or UrlNormalizer()
        self.link_discovery = link_discovery
        self.robots_policy = robots_policy
        self.request_delay_seconds = request_delay_seconds
        self.sleeper = sleeper or time.sleep

    def run(self, crawl: Crawl, stop_token=None):
        stop_token = stop_token or NeverStopToken()
        start_result = self.normalizer.normalize(crawl.config.start_url)
        if not start_result.ok:
            return self._failed_result(crawl, start_result.first_error)

        running_result = crawl.start(self.clock.now())
        if not running_result.ok:
            return self._failed_result(crawl, running_result.first_error)
        crawl = running_result.value

        frontier = UrlFrontier(start_result.value)
        start_allowed = self._robots_allows(start_result.value)
        if start_allowed:
            frontier.add(start_result.value, depth=0)

        publish_error = self._publish(
            CrawlStarted(crawl.crawl_id, self.clock.now(), crawl.config)
        )
        if publish_error:
            return self._fail_running_crawl(crawl, frontier, 0, publish_error)
        if start_allowed:
            publish_error = self._publish(
                UrlQueued(crawl.crawl_id, self.clock.now(), start_result.value)
            )
            if publish_error:
                return self._fail_running_crawl(crawl, frontier, 0, publish_error)

        attempted = 0
        while frontier.successful_page_count < crawl.config.page_limit:
            if stop_token.is_stop_requested():
                return self._stopped_result(crawl, frontier, attempted)

            entry = frontier.next_url()
            if entry is None:
                return self._completed_result(crawl, frontier, attempted)

            if self.request_delay_seconds > 0 and attempted > 0:
                self.sleeper(self.request_delay_seconds)

            fetch_result = self.fetch_port.fetch(entry.url)
            attempted += 1
            if fetch_result.status == FetchStatus.SUCCESS:
                frontier.mark_visited(entry.url, fetch_result)
            else:
                frontier.mark_failed(
                    entry.url, fetch_result.error or fetch_result.status.value
                )

            publish_error = self._publish(
                PageFetched(
                    crawl.crawl_id,
                    self.clock.now(),
                    entry.url,
                    fetch_result.status,
                    fetch_result.status_code,
                )
            )
            if publish_error:
                return self._fail_running_crawl(
                    crawl, frontier, attempted, publish_error
                )

            if self._is_html_success(fetch_result):
                self._discover_and_queue(crawl, frontier, entry, fetch_result)

            publish_error = self._publish_progress(crawl, frontier)
            if publish_error:
                return self._fail_running_crawl(
                    crawl, frontier, attempted, publish_error
                )

            if stop_token.is_stop_requested():
                return self._stopped_result(crawl, frontier, attempted)

        return self._completed_result(crawl, frontier, attempted)

    def _discover_and_queue(self, crawl, frontier, entry, fetch_result):
        if self.link_discovery is None:
            return
        for candidate in self.link_discovery.discover_links(fetch_result):
            href = getattr(candidate, "raw_href", candidate)
            normalized = self.normalizer.normalize_discovered(href, entry.url)
            if not normalized.ok:
                continue
            if not self._robots_allows(normalized.value):
                continue
            add_result = frontier.add(normalized.value, entry.depth + 1)
            if add_result.added:
                self._publish(
                    UrlQueued(crawl.crawl_id, self.clock.now(), normalized.value)
                )

    def _robots_allows(self, url):
        if self.robots_policy is None:
            return True
        try:
            return self.robots_policy.is_allowed(url)
        except Exception:
            return True

    def _is_html_success(self, fetch_result):
        content_type = (fetch_result.content_type or "").lower()
        return fetch_result.status == FetchStatus.SUCCESS and "html" in content_type

    def _publish_progress(self, crawl, frontier):
        snapshot = frontier.snapshot()
        return self._publish(
            CrawlProgressed(
                crawl.crawl_id,
                self.clock.now(),
                snapshot.successful_page_count,
                snapshot.queued_count,
                0,
                snapshot.failed_count,
            )
        )

    def _completed_result(self, crawl, frontier, attempted):
        completed = crawl.complete(self.clock.now()).value
        self._publish(
            CrawlCompleted(
                completed.crawl_id,
                self.clock.now(),
                frontier.successful_page_count,
                0,
                0,
            )
        )
        return CrawlRunResult(
            crawl=completed,
            final_status=completed.status,
            snapshot=frontier.snapshot(),
            successful_page_count=frontier.successful_page_count,
            attempted_fetch_count=attempted,
        )

    def _stopped_result(self, crawl, frontier, attempted):
        stopping = crawl.request_stop(self.clock.now()).value
        stopped = stopping.mark_stopped(self.clock.now()).value
        self._publish(
            CrawlStopped(
                stopped.crawl_id, self.clock.now(), frontier.successful_page_count, 0
            )
        )
        return CrawlRunResult(
            crawl=stopped,
            final_status=stopped.status,
            snapshot=frontier.snapshot(),
            successful_page_count=frontier.successful_page_count,
            attempted_fetch_count=attempted,
        )

    def _fail_running_crawl(self, crawl, frontier, attempted, error):
        failed = crawl.fail(error, self.clock.now()).value
        self._publish(CrawlFailed(failed.crawl_id, self.clock.now(), error))
        return CrawlRunResult(
            crawl=failed,
            final_status=failed.status,
            snapshot=frontier.snapshot(),
            successful_page_count=frontier.successful_page_count,
            attempted_fetch_count=attempted,
            failure=error,
        )

    def _failed_result(self, crawl, error):
        domain_error = _as_domain_error(error)
        return CrawlRunResult(
            crawl=crawl,
            final_status=CrawlStatus.FAILED,
            snapshot=FrontierSnapshot(0, 0, 0, 0, 0),
            successful_page_count=0,
            attempted_fetch_count=0,
            failure=domain_error,
        )

    def _publish(self, event):
        try:
            self.event_publisher.publish(event)
        except Exception as exc:
            return DomainError.of("event.publish_failed", str(exc))
        return None


def _as_domain_error(error):
    if isinstance(error, DomainError):
        return error
    code = getattr(error, "code", "crawl.failed")
    message = getattr(error, "message", str(error))
    return DomainError.of(code, message)
