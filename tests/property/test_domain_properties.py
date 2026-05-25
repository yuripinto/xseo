from dataclasses import FrozenInstanceError
from datetime import UTC, datetime

import pytest
from hypothesis import given
from hypothesis import strategies as st

from tests.strategies.domain import (
    crawl_ids,
    crawl_started_events,
    crawls,
    http_urls,
    invalid_urls,
)
from xseo.domain.enums import CrawlStatus
from xseo.domain.ids import CrawlId, PageId
from xseo.domain.urls import BaseUrl, RawUrl


@given(crawl_ids())
def test_equal_typed_ids_have_stable_hash(crawl_id):
    same = CrawlId.create(crawl_id.value).value

    assert crawl_id == same
    assert hash(crawl_id) == hash(same)


@given(st.text(min_size=1))
def test_different_id_types_are_never_equal(raw):
    crawl_id_result = CrawlId.create(raw)
    page_id_result = PageId.create(raw)

    if crawl_id_result.ok and page_id_result.ok:
        assert crawl_id_result.value != page_id_result.value


@given(http_urls)
def test_valid_http_urls_construct(raw_url):
    assert RawUrl.create(raw_url).ok
    assert BaseUrl.create(raw_url).ok


@given(invalid_urls)
def test_invalid_base_urls_fail(raw_url):
    assert not BaseUrl.create(raw_url).ok


@given(st.text())
def test_crawl_status_enum_rejects_unknown_values(value):
    known = {item.value for item in CrawlStatus}
    if value not in known:
        with pytest.raises(ValueError):
            CrawlStatus(value)


@given(crawl_started_events())
def test_events_preserve_required_payload(event):
    assert event.crawl_id.value
    assert event.occurred_at is not None
    assert event.config.page_limit > 0


@given(crawls())
def test_crawl_transition_does_not_mutate_original(crawl):
    result = crawl.start(datetime(2026, 1, 1, 0, 1, tzinfo=UTC))

    assert result.ok
    assert crawl.status == CrawlStatus.CREATED
    assert result.value.status == CrawlStatus.RUNNING


@given(crawls())
def test_crawl_is_immutable(crawl):
    with pytest.raises(FrozenInstanceError):
        crawl.status = CrawlStatus.RUNNING
