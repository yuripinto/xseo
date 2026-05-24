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
