from hypothesis import given

from tests.strategies.domain import same_host_url_sequences, valid_url_strings
from xseo.domain.frontier import FrontierAddStatus, UrlFrontier, UrlNormalizer


@given(valid_url_strings())
def test_url_normalization_is_idempotent(raw_url):
    normalizer = UrlNormalizer()
    first = normalizer.normalize(raw_url)

    assert first.ok
    second = normalizer.normalize(first.value)

    assert second.ok
    assert second.value == first.value


@given(same_host_url_sequences())
def test_frontier_preserves_queue_uniqueness(urls):
    normalizer = UrlNormalizer()
    start = normalizer.normalize("https://example.com/").value
    frontier = UrlFrontier(start)

    added = 0
    for raw in urls:
        normalized = normalizer.normalize(raw)
        if normalized.ok and frontier.add(normalized.value, depth=1).status == FrontierAddStatus.ADDED:
            added += 1

    snapshot = frontier.snapshot()
    assert snapshot.queued_count == added
    assert added <= len({normalizer.normalize(raw).value.value for raw in urls})


@given(valid_url_strings(host="other.example.com"))
def test_frontier_rejects_off_host_urls(raw_url):
    normalizer = UrlNormalizer()
    frontier = UrlFrontier(normalizer.normalize("https://example.com/").value)

    result = frontier.add(normalizer.normalize(raw_url).value, depth=1)

    assert result.status == FrontierAddStatus.OFF_HOST
