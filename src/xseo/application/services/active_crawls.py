"""Active crawl control registry."""

from __future__ import annotations

from dataclasses import dataclass

from xseo.application.results import ApplicationResult


@dataclass(frozen=True)
class ActiveCrawl:
    crawl_id: object
    control_handle: object
    status: object | None = None
    terminal: bool = False
    stop_requested: bool = False


class ActiveCrawlRegistry:
    def __init__(self):
        self._active = {}

    def register(self, crawl_id, control_handle, status=None):
        key = _key(crawl_id)
        if key in self._active and not self._active[key].terminal:
            return ApplicationResult.fail(
                "Crawl is already active", "crawl.already_active", self._active[key]
            )
        active = ActiveCrawl(crawl_id, control_handle, status=status)
        self._active[key] = active
        return ApplicationResult.ok(active)

    def request_stop(self, crawl_id):
        key = _key(crawl_id)
        active = self._active.get(key)
        if active is None:
            return ApplicationResult.fail("Crawl is not active", "crawl.not_active")
        if active.stop_requested or active.terminal:
            return ApplicationResult.ok(active)
        if hasattr(active.control_handle, "request_stop"):
            active.control_handle.request_stop()
        elif hasattr(active.control_handle, "stop"):
            active.control_handle.stop()
        active = ActiveCrawl(
            active.crawl_id, active.control_handle, active.status, active.terminal, True
        )
        self._active[key] = active
        return ApplicationResult.ok(active)

    def mark_terminal(self, crawl_id, status=None):
        key = _key(crawl_id)
        active = self._active.get(key)
        if active is None:
            active = ActiveCrawl(crawl_id, None, status=status, terminal=True)
        else:
            active = ActiveCrawl(
                active.crawl_id,
                active.control_handle,
                status or active.status,
                True,
                active.stop_requested,
            )
        self._active[key] = active
        return ApplicationResult.ok(active)

    def get(self, crawl_id):
        active = self._active.get(_key(crawl_id))
        if active is None:
            return ApplicationResult.fail("Crawl is not active", "crawl.not_active")
        return ApplicationResult.ok(active)


def _key(crawl_id):
    return getattr(crawl_id, "value", str(crawl_id))
