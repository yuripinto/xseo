"""Threaded background execution adapter."""

from __future__ import annotations

from inspect import signature
from threading import Event, Lock, Thread


class StopToken:
    def __init__(self):
        self._event = Event()

    def request_stop(self):
        self._event.set()

    def is_stop_requested(self) -> bool:
        return self._event.is_set()

    @property
    def requested(self) -> bool:
        return self._event.is_set()

    def wait(self, timeout=None):
        return self._event.wait(timeout)


class BackgroundHandle:
    def __init__(self, crawl_id, work):
        self.crawl_id = crawl_id
        self.stop_token = StopToken()
        self.result = None
        self.error = None
        self._done = Event()
        self._thread = Thread(target=self._run, args=(work,), daemon=True)
        self._thread.start()

    def request_stop(self):
        self.stop_token.request_stop()

    def stop(self):
        self.request_stop()

    def join(self, timeout=None):
        self._thread.join(timeout)
        return self.result

    def is_running(self):
        return self._thread.is_alive()

    @property
    def done(self):
        return self._done.is_set()

    def _run(self, work):
        try:
            self.result = _call_work(work, self.stop_token)
        except Exception as exc:
            self.error = exc
        finally:
            self._done.set()


class ThreadedBackgroundExecution:
    def __init__(self):
        self._handles = {}
        self._lock = Lock()

    def start(self, crawl_id, work):
        handle = BackgroundHandle(crawl_id, work)
        with self._lock:
            self._handles[_key(crawl_id)] = handle
        return handle

    def request_stop(self, crawl_id):
        handle = self._handles.get(_key(crawl_id))
        if handle is not None:
            handle.request_stop()
        return handle

    def is_running(self, crawl_id):
        handle = self._handles.get(_key(crawl_id))
        return bool(handle and handle.is_running())

    def get(self, crawl_id):
        return self._handles.get(_key(crawl_id))


def _call_work(work, stop_token):
    parameters = signature(work).parameters
    if not parameters:
        return work()
    return work(stop_token)


def _key(crawl_id):
    return getattr(crawl_id, "value", str(crawl_id))
