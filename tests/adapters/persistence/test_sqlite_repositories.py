from datetime import UTC, datetime

from xseo.adapters.persistence import (
    SQLiteAnalysisRepository,
    SQLiteCrawlDataRepository,
    SQLiteCrawlRepository,
    SQLiteDatabase,
    SQLiteExportRepository,
    SQLiteResultsReadRepository,
)
from xseo.application.commands import PageDetailQuery, QueryOptions, ResultQuery
from xseo.domain.entities import (
    Crawl,
    CrawlConfig,
    DuplicateGroup,
    ExportResult,
    ExtractedPage,
    Heading,
    Issue,
    PageLink,
    Redirect,
)
from xseo.domain.enums import (
    CrawlStatus,
    ExportKind,
    HeadingLevel,
    IssueSeverity,
    IssueType,
    LinkRelation,
)
from xseo.domain.ids import CrawlId, DuplicateGroupId, ExportId, IssueId, PageId
from xseo.domain.urls import BaseUrl, NormalizedUrl
from xseo.domain.value_objects import ContentHash, FilePath, WordCount


def connection():
    return SQLiteDatabase.memory().initialize().connect()


def id_(cls, value):
    return cls.create(value).value


def url(value):
    return NormalizedUrl.create(value).value


def crawl(crawl_id=None, created_at=None):
    crawl_id = crawl_id or id_(CrawlId, "crawl-1")
    config = CrawlConfig.create(BaseUrl.create("https://example.com/").value).value
    return Crawl(
        crawl_id,
        config,
        CrawlStatus.CREATED,
        created_at or datetime(2026, 1, 1, tzinfo=UTC),
    )


def page(crawl_id=None, page_id=None, path="page"):
    crawl_id = crawl_id or id_(CrawlId, "crawl-1")
    page_id = page_id or id_(PageId, f"page-{path}")
    page_url = url(f"https://example.com/{path}")
    return ExtractedPage(
        page_id,
        crawl_id,
        page_url,
        page_url,
        200,
        "text/html",
        "Title",
        "Description",
        None,
        None,
        WordCount.create(120).value,
        1234,
        ContentHash.create(f"hash-{path}").value,
    )


def test_schema_initialization_is_idempotent():
    database = SQLiteDatabase.memory().initialize()
    database.initialize()
    conn = database.connect()

    version = conn.execute("SELECT version FROM schema_version").fetchone()[0]

    assert version == 1


def test_migration_adds_image_columns_to_legacy_pages_table():
    import sqlite3

    from xseo.adapters.persistence.database import _apply_column_migrations

    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE pages (
            page_id TEXT PRIMARY KEY,
            crawl_id TEXT NOT NULL,
            url TEXT NOT NULL,
            final_url TEXT NOT NULL,
            status_code INTEGER NOT NULL,
            content_type TEXT,
            title TEXT,
            meta_description TEXT,
            canonical_url TEXT,
            robots_meta TEXT,
            word_count INTEGER NOT NULL,
            content_length INTEGER NOT NULL,
            content_hash TEXT
        )
        """
    )
    conn.execute(
        "INSERT INTO pages(page_id, crawl_id, url, final_url, status_code, "
        "word_count, content_length) VALUES ('p1','c1','u','u',200,10,100)"
    )

    _apply_column_migrations(conn)
    _apply_column_migrations(conn)  # idempotent: running again is a no-op

    columns = {row["name"] for row in conn.execute("PRAGMA table_info(pages)")}
    assert {
        "image_count",
        "images_missing_alt",
        "has_viewport",
        "has_lang",
        "has_charset",
        "depth",
        "images_missing_dimensions",
        "structured_data_invalid",
    } <= columns
    assert (
        conn.execute("SELECT depth FROM pages WHERE page_id = 'p1'").fetchone()["depth"]
        == 0
    )
    legacy_row = conn.execute(
        "SELECT image_count, images_missing_alt, has_viewport, has_lang, has_charset "
        "FROM pages WHERE page_id = 'p1'"
    ).fetchone()
    assert legacy_row["image_count"] == 0
    assert legacy_row["images_missing_alt"] == 0
    assert legacy_row["has_viewport"] == 0
    assert legacy_row["has_lang"] == 0
    assert legacy_row["has_charset"] == 0


def test_crawl_round_trip_and_recent_selection():
    conn = connection()
    repo = SQLiteCrawlRepository(conn)
    older = crawl(id_(CrawlId, "crawl-a"), datetime(2026, 1, 1, tzinfo=UTC))
    newer = crawl(id_(CrawlId, "crawl-b"), datetime(2026, 1, 2, tzinfo=UTC))

    repo.save_crawl(older)
    repo.save_crawl(newer)

    assert repo.get_crawl(older.crawl_id) == older
    assert repo.find_recent_crawl() == newer


def test_page_related_data_and_detail_round_trip():
    conn = connection()
    SQLiteCrawlRepository(conn).save_crawl(crawl())
    data_repo = SQLiteCrawlDataRepository(conn)
    read_repo = SQLiteResultsReadRepository(conn)
    saved_page = page()
    link = PageLink(
        saved_page.page_id,
        url("https://example.com/target"),
        LinkRelation.INTERNAL,
        "target",
    )
    heading = Heading(saved_page.page_id, HeadingLevel.H1, "Heading", 1)
    redirect = Redirect(
        saved_page.crawl_id, url("https://example.com/old"), saved_page.url, 301
    )

    data_repo.save_page(saved_page)
    data_repo.save_links(saved_page.page_id, (link,))
    data_repo.save_headings(saved_page.page_id, (heading,))
    data_repo.save_redirect(redirect)

    detail = read_repo.get_page_detail(
        PageDetailQuery(saved_page.crawl_id, saved_page.page_id)
    )

    assert detail.page.page_id == saved_page.page_id
    assert detail.headings == (heading,)
    assert detail.outlinks == (link,)
    assert detail.redirects == (redirect,)
    assert detail.content_hash == saved_page.content_hash


def test_page_depth_round_trips_through_persistence():
    from dataclasses import replace

    conn = connection()
    SQLiteCrawlRepository(conn).save_crawl(crawl())
    data_repo = SQLiteCrawlDataRepository(conn)
    deep_page = replace(page(), depth=3)

    data_repo.save_page(deep_page)
    loaded = data_repo.load_analysis_data(deep_page.crawl_id).pages[0]

    assert loaded.depth == 3


def test_issue_and_duplicate_group_reads_are_deterministic():
    conn = connection()
    crawl_repo = SQLiteCrawlRepository(conn)
    data_repo = SQLiteCrawlDataRepository(conn)
    analysis_repo = SQLiteAnalysisRepository(conn)
    read_repo = SQLiteResultsReadRepository(conn)
    saved_crawl = crawl()
    first = page(path="first")
    second = page(page_id=id_(PageId, "page-second"), path="second")
    crawl_repo.save_crawl(saved_crawl)
    data_repo.save_page(first)
    data_repo.save_page(second)
    issue = Issue(
        id_(IssueId, "issue-1"),
        saved_crawl.crawl_id,
        first.page_id,
        first.url,
        IssueType.TITLE_MISSING,
        IssueSeverity.MEDIUM,
        "Missing title",
    )
    group = DuplicateGroup.create(
        id_(DuplicateGroupId, "group-1"),
        saved_crawl.crawl_id,
        ContentHash.create("shared-hash").value,
        (first.page_id, second.page_id),
    ).value

    analysis_repo.save_issues(saved_crawl.crawl_id, (issue,))
    analysis_repo.save_duplicate_groups(saved_crawl.crawl_id, (group,))

    issues = read_repo.list_issues(
        ResultQuery(saved_crawl.crawl_id, QueryOptions(sort_field="issue_type"))
    )
    groups = read_repo.list_duplicate_groups(
        ResultQuery(saved_crawl.crawl_id, QueryOptions(sort_field="content_hash"))
    )

    assert issues[0].issue_id == issue.issue_id
    assert groups[0].page_count == 2


def test_export_metadata_and_export_rows():
    conn = connection()
    saved_crawl = crawl()
    SQLiteCrawlRepository(conn).save_crawl(saved_crawl)
    SQLiteCrawlDataRepository(conn).save_page(page())
    export_result = ExportResult.create(
        id_(ExportId, "export-1"),
        saved_crawl.crawl_id,
        ExportKind.PAGES,
        FilePath.create("/tmp/pages.csv").value,
        1,
        True,
    ).value

    SQLiteExportRepository(conn).save_export(export_result)
    rows = SQLiteResultsReadRepository(conn).list_pages_for_export(saved_crawl.crawl_id)

    assert len(rows) == 1
    assert conn.execute("SELECT COUNT(*) FROM exports").fetchone()[0] == 1


def test_idempotent_saves_do_not_duplicate_rows():
    conn = connection()
    repo = SQLiteCrawlRepository(conn)
    saved = crawl()

    repo.save_crawl(saved)
    repo.save_crawl(saved)

    assert conn.execute("SELECT COUNT(*) FROM crawls").fetchone()[0] == 1
