from xseo.domain.entities import CrawlConfig
from xseo.domain.urls import BaseUrl


def test_crawl_config_accepts_positive_limits():
    base_url = BaseUrl.create("https://example.com").value

    result = CrawlConfig.create(base_url, page_limit=10, timeout_seconds=5)

    assert result.ok
    assert result.value.page_limit == 10


def test_crawl_config_rejects_zero_page_limit():
    base_url = BaseUrl.create("https://example.com").value

    result = CrawlConfig.create(base_url, page_limit=0, timeout_seconds=5)

    assert not result.ok


def test_crawl_config_defaults_delay_and_respect_robots():
    base_url = BaseUrl.create("https://example.com").value

    result = CrawlConfig.create(base_url)

    assert result.ok
    assert result.value.request_delay_seconds == 0.5
    assert result.value.respect_robots is True


def test_crawl_config_rejects_negative_request_delay():
    base_url = BaseUrl.create("https://example.com").value

    result = CrawlConfig.create(base_url, request_delay_seconds=-1.0)

    assert not result.ok


def test_crawl_config_accepts_zero_request_delay():
    base_url = BaseUrl.create("https://example.com").value

    result = CrawlConfig.create(base_url, request_delay_seconds=0.0, respect_robots=False)

    assert result.ok
    assert result.value.request_delay_seconds == 0.0
    assert result.value.respect_robots is False
