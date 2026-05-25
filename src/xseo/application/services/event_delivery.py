"""Ordered in-process event delivery."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import count

from xseo.application.results import ApplicationResult


@dataclass(frozen=True)
class Subscription:
    subscription_id: str
    crawl_id: object
    callback: object


@dataclass(frozen=True)
class PublishResult:
    delivered_count: int
    errors: tuple[Exception, ...] = ()


class EventDeliveryService:
    def __init__(self):
        self._counter = count(1)
        self._subscribers = {}
        self._subscription_index = {}

    def subscribe(self, crawl_id, callback):
        subscription = Subscription(
            f"subscription-{next(self._counter)}", crawl_id, callback
        )
        key = _key(crawl_id)
        self._subscribers.setdefault(key, []).append(subscription)
        self._subscription_index[subscription.subscription_id] = key
        return ApplicationResult.ok(subscription)

    def unsubscribe(self, subscription_id):
        key = self._subscription_index.pop(subscription_id, None)
        if key is None:
            return ApplicationResult.ok(False)
        self._subscribers[key] = [
            subscription
            for subscription in self._subscribers.get(key, ())
            if subscription.subscription_id != subscription_id
        ]
        return ApplicationResult.ok(True)

    def publish(self, event):
        errors = []
        delivered = 0
        for subscription in tuple(self._subscribers.get(_key(event.crawl_id), ())):
            try:
                subscription.callback(event)
                delivered += 1
            except Exception as exc:
                errors.append(exc)
        return ApplicationResult.ok(PublishResult(delivered, tuple(errors)))


def _key(crawl_id):
    return getattr(crawl_id, "value", str(crawl_id))
