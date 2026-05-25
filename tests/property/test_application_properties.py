from datetime import UTC, datetime

from hypothesis import given
from hypothesis import strategies as st

from tests.strategies.domain import (
    crawl_ids,
    crawl_progress_events,
    page_rows,
    query_options,
    stop_request_counts,
)
from xseo.application.events import CrawlProgressEvent, CrawlProgressEventKind
from xseo.application.query import apply_query_options
from xseo.application.services import ActiveCrawlRegistry, EventDeliveryService
from xseo.domain.enums import CrawlStatus


class StopHandle:
    def __init__(self):
        self.stop_count = 0

    def request_stop(self):
        self.stop_count += 1


@given(crawl_ids(), st.lists(st.text(max_size=20), min_size=0, max_size=20))
def test_event_delivery_preserves_publish_order(crawl_id, messages):
    service = EventDeliveryService()
    delivered = []
    service.subscribe(crawl_id, lambda event: delivered.append(event.message))

    for message in messages:
        service.publish(
            CrawlProgressEvent(
                crawl_id,
                CrawlProgressEventKind.STATUS_CHANGED,
                CrawlStatus.RUNNING,
                datetime(2026, 1, 1, tzinfo=UTC),
                message,
            )
        )

    assert delivered == messages


@given(crawl_progress_events())
def test_unsubscribe_is_idempotent(event):
    service = EventDeliveryService()
    delivered = []
    subscription = service.subscribe(
        event.crawl_id, lambda delivered_event: delivered.append(delivered_event)
    ).value

    assert service.unsubscribe(subscription.subscription_id).success
    assert service.unsubscribe(subscription.subscription_id).success
    service.publish(event)

    assert delivered == []


@given(crawl_ids(), stop_request_counts)
def test_repeated_stop_requests_are_stable(crawl_id, count):
    registry = ActiveCrawlRegistry()
    handle = StopHandle()
    registry.register(crawl_id, handle)

    results = [registry.request_stop(crawl_id) for _ in range(count)]

    assert all(result.success for result in results)
    assert handle.stop_count == 1
    assert all(result.value.stop_requested for result in results)


@given(st.lists(page_rows(), min_size=0, max_size=20), query_options)
def test_query_sort_filter_output_is_deterministic(rows, options):
    allowed = {"url", "status_code", "title", "word_count"}

    first = apply_query_options(rows, options, allowed)
    second = apply_query_options(rows, options, allowed)

    assert first == second
