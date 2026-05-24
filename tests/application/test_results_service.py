from xseo.application import PageRow, QueryOptions, ResultQuery
from xseo.application.query import apply_query_options
from xseo.application.services import ResultsApplicationService
from xseo.domain.ids import CrawlId, PageId
from xseo.domain.urls import NormalizedUrl


def _id(cls, value):
    return cls.create(value).value


def _url(value):
    return NormalizedUrl.create(value).value


def _row(page_id, path, status_code, title):
    url = _url(f"https://example.com/{path}")
    return PageRow(_id(PageId, page_id), url, url, status_code, title, None, None, 100, "text/html")


class ReadRepository:
    def __init__(self, rows):
        self.rows = tuple(rows)

    def list_pages(self, query):
        return apply_query_options(
            self.rows,
            query.options,
            {"url", "final_url", "status_code", "title", "word_count", "content_type"},
        ).value

    def list_issues(self, query):
        return ()

    def list_duplicate_groups(self, query):
        return ()

    def get_page_detail(self, query):
        return None

    def find_recent_crawl(self):
        return None


def test_results_service_returns_sorted_page_rows():
    rows = (_row("page-2", "b", 404, "B"), _row("page-1", "a", 200, "A"))
    service = ResultsApplicationService(ReadRepository(rows))
    query = ResultQuery(_id(CrawlId, "crawl-1"), QueryOptions(sort_field="status_code"))

    result = service.list_pages(query)

    assert result.success
    assert [row.status_code for row in result.value] == [200, 404]


def test_results_service_rejects_invalid_sort_field():
    service = ResultsApplicationService(ReadRepository(()))
    query = ResultQuery(_id(CrawlId, "crawl-1"), QueryOptions(sort_field="missing"))

    result = service.list_pages(query)

    assert not result.success
    assert result.error_code == "query.invalid_sort_field"
