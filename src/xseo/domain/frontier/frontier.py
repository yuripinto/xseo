"""Deterministic in-memory URL frontier."""

from __future__ import annotations

from collections import deque
from dataclasses import replace
from urllib.parse import urlparse

from xseo.domain.entities import FetchResult
from xseo.domain.enums import FetchStatus
from xseo.domain.frontier.results import (
    FrontierAddResult,
    FrontierAddStatus,
    FrontierAddSummary,
    FrontierEntry,
    FrontierEntryState,
    FrontierSnapshot,
    RejectionReason,
)
from xseo.domain.urls import NormalizedUrl


class UrlFrontier:
    def __init__(self, start_url: NormalizedUrl):
        self.start_url = start_url
        self._allowed_host = urlparse(start_url.value).hostname
        self._queue = deque()
        self._entries = {}
        self._successful_page_count = 0
        self._current_url = None

    def add(self, url: NormalizedUrl, depth: int):
        key = url.value
        if key in self._entries:
            return FrontierAddResult(
                status=FrontierAddStatus.DUPLICATE,
                url=url,
                reason=RejectionReason.DUPLICATE,
            )
        if not self._is_allowed_host(url):
            self._entries[key] = FrontierEntry(
                url=url,
                depth=depth,
                state=FrontierEntryState.REJECTED,
                rejection_reason=RejectionReason.OFF_HOST,
            )
            return FrontierAddResult(
                status=FrontierAddStatus.OFF_HOST,
                url=url,
                reason=RejectionReason.OFF_HOST,
            )

        self._entries[key] = FrontierEntry(
            url=url,
            depth=depth,
            state=FrontierEntryState.QUEUED,
        )
        self._queue.append(url)
        return FrontierAddResult(status=FrontierAddStatus.ADDED, url=url)

    def add_many(self, urls, source_depth: int):
        counts = {
            "added_count": 0,
            "duplicate_count": 0,
            "invalid_count": 0,
            "off_host_count": 0,
            "rejected_count": 0,
        }
        for url in urls:
            result = self.add(url, source_depth + 1)
            if result.status == FrontierAddStatus.ADDED:
                counts["added_count"] += 1
            elif result.status == FrontierAddStatus.DUPLICATE:
                counts["duplicate_count"] += 1
            elif result.status == FrontierAddStatus.INVALID:
                counts["invalid_count"] += 1
            elif result.status == FrontierAddStatus.OFF_HOST:
                counts["off_host_count"] += 1
            else:
                counts["rejected_count"] += 1
        return FrontierAddSummary(**counts)

    def next_url(self):
        while self._queue:
            url = self._queue.popleft()
            entry = self._entries.get(url.value)
            if entry and entry.state == FrontierEntryState.QUEUED:
                self._current_url = url
                return entry
        self._current_url = None
        return None

    def mark_visited(self, url: NormalizedUrl, fetch_result: FetchResult):
        entry = self._entries[url.value]
        self._entries[url.value] = replace(entry, state=FrontierEntryState.VISITED)
        if fetch_result.status == FetchStatus.SUCCESS:
            self._successful_page_count += 1

    def mark_failed(self, url: NormalizedUrl, failure):
        entry = self._entries[url.value]
        message = getattr(failure, "message", str(failure))
        self._entries[url.value] = replace(
            entry,
            state=FrontierEntryState.FAILED,
            failure_message=message,
        )

    def reject(self, url: NormalizedUrl, reason: RejectionReason):
        self._entries[url.value] = FrontierEntry(
            url=url,
            depth=0,
            state=FrontierEntryState.REJECTED,
            rejection_reason=reason,
        )

    def entry_for(self, url: NormalizedUrl):
        return self._entries.get(url.value)

    def snapshot(self):
        counts = {state: 0 for state in FrontierEntryState}
        max_depth = None
        for entry in self._entries.values():
            counts[entry.state] += 1
            max_depth = (
                entry.depth if max_depth is None else max(max_depth, entry.depth)
            )
        return FrontierSnapshot(
            queued_count=counts[FrontierEntryState.QUEUED],
            visited_count=counts[FrontierEntryState.VISITED],
            rejected_count=counts[FrontierEntryState.REJECTED],
            failed_count=counts[FrontierEntryState.FAILED],
            successful_page_count=self._successful_page_count,
            current_url=self._current_url,
            maximum_depth=max_depth,
        )

    @property
    def successful_page_count(self):
        return self._successful_page_count

    def _is_allowed_host(self, url: NormalizedUrl):
        return urlparse(url.value).hostname == self._allowed_host
