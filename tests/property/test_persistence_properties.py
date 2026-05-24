from datetime import UTC, datetime

from hypothesis import given
from hypothesis import strategies as st

from tests.adapters.persistence.test_sqlite_repositories import connection, crawl, id_, page
from tests.strategies.domain import query_options
from xseo.adapters.persistence import SQLiteCrawlDataRepository, SQLiteCrawlRepository, SQLiteResultsReadRepository
from xseo.application.commands import ResultQuery
from xseo.domain.ids import CrawlId, PageId


@given(st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789-", min_size=1, max_size=24))
def test_crawl_round_trip_preserves_stable_fields(suffix):
    conn = connection()
    repo = SQLiteCrawlRepository(conn)
    saved = crawl(id_(CrawlId, f"crawl-{suffix}"), datetime(2026, 1, 1, tzinfo=UTC))

    repo.save_crawl(saved)
    loaded = repo.get_crawl(saved.crawl_id)

    assert loaded.crawl_id == saved.crawl_id
    assert loaded.config == saved.config
    assert loaded.status == saved.status
    assert loaded.created_at == saved.created_at


@given(st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789-", min_size=1, max_size=24))
def test_page_read_model_round_trip_preserves_stable_fields(suffix):
    conn = connection()
    saved_crawl = crawl()
    saved_page = page(page_id=id_(PageId, f"page-{suffix}"), path=suffix)
    SQLiteCrawlRepository(conn).save_crawl(saved_crawl)
    SQLiteCrawlDataRepository(conn).save_page(saved_page)

    rows = SQLiteResultsReadRepository(conn).list_pages(ResultQuery(saved_crawl.crawl_id))

    assert rows[0].page_id == saved_page.page_id
    assert rows[0].url == saved_page.url
    assert rows[0].status_code == saved_page.status_code


@given(st.integers(min_value=1, max_value=10))
def test_repeated_page_saves_are_idempotent(count):
    conn = connection()
    saved_crawl = crawl()
    saved_page = page()
    SQLiteCrawlRepository(conn).save_crawl(saved_crawl)
    repo = SQLiteCrawlDataRepository(conn)

    for _ in range(count):
        repo.save_page(saved_page)

    assert conn.execute("SELECT COUNT(*) FROM pages").fetchone()[0] == 1


@given(query_options)
def test_sqlite_query_output_is_deterministic(options):
    conn = connection()
    saved_crawl = crawl()
    SQLiteCrawlRepository(conn).save_crawl(saved_crawl)
    data_repo = SQLiteCrawlDataRepository(conn)
    data_repo.save_page(page(path="a"))
    data_repo.save_page(page(page_id=id_(PageId, "page-b"), path="b"))
    read_repo = SQLiteResultsReadRepository(conn)
    query = ResultQuery(saved_crawl.crawl_id, options)

    first = read_repo.list_pages(query)
    second = read_repo.list_pages(query)

    assert first == second
