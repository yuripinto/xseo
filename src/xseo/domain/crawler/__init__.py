"""Domain crawl loop behavior."""

from xseo.domain.crawler.engine import CrawlRunResult, LinkDiscoveryPort, UrlCrawlEngine
from xseo.domain.crawler.stop import NeverStopToken, StopToken

__all__ = [
    "CrawlRunResult",
    "LinkDiscoveryPort",
    "NeverStopToken",
    "StopToken",
    "UrlCrawlEngine",
]
