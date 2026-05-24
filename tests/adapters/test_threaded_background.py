from threading import Event

from xseo.adapters.background import ThreadedBackgroundExecution
from xseo.domain.ids import CrawlId


def _crawl_id(value="crawl-1"):
    return CrawlId.create(value).value


def test_threaded_background_runs_work_and_stores_result():
    background = ThreadedBackgroundExecution()

    handle = background.start(_crawl_id(), lambda: "done")

    assert handle.join(1) == "done"
    assert handle.done
    assert not background.is_running(_crawl_id())


def test_threaded_background_passes_stop_token():
    background = ThreadedBackgroundExecution()
    started = Event()

    def work(stop_token):
        started.set()
        stop_token.wait(1)
        return stop_token.requested

    crawl_id = _crawl_id()
    handle = background.start(crawl_id, work)
    assert started.wait(1)
    background.request_stop(crawl_id)

    assert handle.join(1) is True
    assert handle.error is None


def test_stop_token_satisfies_domain_protocol():
    """StopToken must implement is_stop_requested() per domain StopToken protocol."""
    from xseo.adapters.background.threaded import StopToken

    token = StopToken()
    assert token.is_stop_requested() is False
    token.request_stop()
    assert token.is_stop_requested() is True


def test_threaded_background_stop_token_compatible_with_engine():
    """Work function calling is_stop_requested() must not error — verifies
    the adapter StopToken satisfies the domain StopToken protocol used by UrlCrawlEngine."""
    background = ThreadedBackgroundExecution()

    def work(stop_token):
        # Mirror what UrlCrawlEngine does on every loop iteration
        if stop_token.is_stop_requested():
            return "stopped"
        return "completed"

    handle = background.start(_crawl_id(), work)
    result = handle.join(1)
    assert handle.error is None, f"Background thread crashed: {handle.error}"
    assert result == "completed"
