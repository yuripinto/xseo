from datetime import UTC, datetime

from xseo.application import CrawlProgressEvent, CrawlProgressEventKind
from xseo.application.services import EventDeliveryService
from xseo.domain.enums import CrawlStatus
from xseo.domain.ids import CrawlId


def _crawl_id(value="crawl-1"):
    return CrawlId.create(value).value


def _event(crawl_id=None, message="event"):
    return CrawlProgressEvent(
        crawl_id or _crawl_id(),
        CrawlProgressEventKind.STATUS_CHANGED,
        CrawlStatus.RUNNING,
        datetime(2026, 1, 1, tzinfo=UTC),
        message,
    )


def test_event_delivery_preserves_order_and_crawl_scope():
    service = EventDeliveryService()
    crawl_id = _crawl_id()
    delivered = []

    service.subscribe(crawl_id, lambda event: delivered.append(event.message))
    service.publish(_event(_crawl_id("crawl-2"), "other"))
    service.publish(_event(crawl_id, "first"))
    service.publish(_event(crawl_id, "second"))

    assert delivered == ["first", "second"]


def test_unsubscribe_is_idempotent_and_prevents_later_delivery():
    service = EventDeliveryService()
    delivered = []
    subscription = service.subscribe(
        _crawl_id(), lambda event: delivered.append(event)
    ).value

    assert service.unsubscribe(subscription.subscription_id).success
    assert service.unsubscribe(subscription.subscription_id).success
    service.publish(_event())

    assert delivered == []


def test_subscriber_failure_does_not_block_other_subscribers():
    service = EventDeliveryService()
    delivered = []

    def failing(_event):
        raise RuntimeError("callback failed")

    service.subscribe(_crawl_id(), failing)
    service.subscribe(_crawl_id(), lambda event: delivered.append(event.message))

    result = service.publish(_event(message="ok"))

    assert result.success
    assert result.value.delivered_count == 1
    assert len(result.value.errors) == 1
    assert delivered == ["ok"]
