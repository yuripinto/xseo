"""SQLite repository adapters."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from xseo.application.commands import QueryOptions, ResultQuery
from xseo.application.read_models import (
    DuplicateGroupRow,
    IssueRow,
    PageDetail,
    PageRow,
)
from xseo.domain.entities import (
    Crawl,
    CrawlConfig,
    ExtractedPage,
    Heading,
    PageLink,
    Redirect,
)
from xseo.domain.enums import (
    CrawlStatus,
    HeadingLevel,
    IssueSeverity,
    IssueType,
    LinkRelation,
)
from xseo.domain.errors import DomainError
from xseo.domain.ids import CrawlId, DuplicateGroupId, IssueId, PageId
from xseo.domain.urls import BaseUrl, NormalizedUrl
from xseo.domain.value_objects import ContentHash, WordCount


@dataclass(frozen=True)
class AnalysisData:
    pages: tuple[ExtractedPage, ...]
    headings: tuple[Heading, ...]
    links: tuple[PageLink, ...]
    redirects: tuple[Redirect, ...]
    link_statuses: tuple = ()


class SQLiteCrawlRepository:
    def __init__(self, connection):
        self.connection = connection

    def save_crawl(self, crawl):
        self.connection.execute(
            """
            INSERT INTO crawls(
                crawl_id, start_url, same_host_only, page_limit, timeout_seconds,
                status, created_at, started_at, completed_at, failure_code, failure_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(crawl_id) DO UPDATE SET
                start_url=excluded.start_url,
                same_host_only=excluded.same_host_only,
                page_limit=excluded.page_limit,
                timeout_seconds=excluded.timeout_seconds,
                status=excluded.status,
                created_at=excluded.created_at,
                started_at=excluded.started_at,
                completed_at=excluded.completed_at,
                failure_code=excluded.failure_code,
                failure_message=excluded.failure_message
            """,
            _crawl_params(crawl),
        )
        self.connection.commit()
        return crawl.crawl_id

    def update_crawl(self, crawl):
        self.save_crawl(crawl)

    def get_crawl(self, crawl_id):
        row = self.connection.execute(
            "SELECT * FROM crawls WHERE crawl_id = ?",
            (_value(crawl_id),),
        ).fetchone()
        return _crawl_from_row(row) if row else None

    def find_recent_crawl(self):
        row = self.connection.execute(
            "SELECT * FROM crawls ORDER BY created_at DESC, crawl_id DESC LIMIT 1"
        ).fetchone()
        return _crawl_from_row(row) if row else None


class SQLiteCrawlDataRepository:
    def __init__(self, connection):
        self.connection = connection

    def save_page(self, page):
        self.connection.execute(
            """
            INSERT INTO pages(
                page_id, crawl_id, url, final_url, status_code, content_type, title,
                meta_description, canonical_url, robots_meta, word_count, content_length, content_hash,
                image_count, images_missing_alt, has_viewport, has_lang, has_charset
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(page_id) DO UPDATE SET
                crawl_id=excluded.crawl_id,
                url=excluded.url,
                final_url=excluded.final_url,
                status_code=excluded.status_code,
                content_type=excluded.content_type,
                title=excluded.title,
                meta_description=excluded.meta_description,
                canonical_url=excluded.canonical_url,
                robots_meta=excluded.robots_meta,
                word_count=excluded.word_count,
                content_length=excluded.content_length,
                content_hash=excluded.content_hash,
                image_count=excluded.image_count,
                images_missing_alt=excluded.images_missing_alt,
                has_viewport=excluded.has_viewport,
                has_lang=excluded.has_lang,
                has_charset=excluded.has_charset
            """,
            _page_params(page),
        )
        self.connection.commit()
        return page.page_id

    def save_links(self, page_id, links):
        with self.connection:
            for link in links:
                self.connection.execute(
                    """
                    INSERT OR REPLACE INTO links(source_page_id, target_url, relation, anchor_text, nofollow)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        _value(page_id),
                        link.target_url.value,
                        link.relation.value,
                        link.anchor_text,
                        int(link.nofollow),
                    ),
                )

    def save_headings(self, page_id, headings):
        with self.connection:
            for heading in headings:
                self.connection.execute(
                    """
                    INSERT OR REPLACE INTO headings(page_id, level, text, position)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        _value(page_id),
                        heading.level.value,
                        heading.text,
                        heading.position,
                    ),
                )

    def save_redirect(self, redirect):
        self.connection.execute(
            """
            INSERT OR REPLACE INTO redirects(crawl_id, from_url, to_url, status_code)
            VALUES (?, ?, ?, ?)
            """,
            (
                redirect.crawl_id.value,
                redirect.from_url.value,
                redirect.to_url.value,
                redirect.status_code,
            ),
        )
        self.connection.commit()

    def load_analysis_data(self, crawl_id):
        pages = tuple(
            _page_from_row(row)
            for row in self.connection.execute(
                "SELECT * FROM pages WHERE crawl_id = ? ORDER BY page_id",
                (_value(crawl_id),),
            )
        )
        headings = tuple(
            _heading_from_row(row)
            for row in self.connection.execute(
                """
                SELECT h.* FROM headings h
                JOIN pages p ON p.page_id = h.page_id
                WHERE p.crawl_id = ?
                ORDER BY h.page_id, h.position
                """,
                (_value(crawl_id),),
            )
        )
        links = tuple(
            _link_from_row(row)
            for row in self.connection.execute(
                """
                SELECT l.* FROM links l
                JOIN pages p ON p.page_id = l.source_page_id
                WHERE p.crawl_id = ?
                ORDER BY l.source_page_id, l.target_url
                """,
                (_value(crawl_id),),
            )
        )
        redirects = tuple(
            _redirect_from_row(row)
            for row in self.connection.execute(
                "SELECT * FROM redirects WHERE crawl_id = ? ORDER BY from_url, to_url",
                (_value(crawl_id),),
            )
        )
        return AnalysisData(pages, headings, links, redirects)


class SQLiteAnalysisRepository:
    def __init__(self, connection):
        self.connection = connection

    def save_issues(self, crawl_id, issues):
        with self.connection:
            for issue in issues:
                self.connection.execute(
                    """
                    INSERT OR REPLACE INTO issues(
                        issue_id, crawl_id, page_id, affected_url, issue_type, severity, explanation
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        issue.issue_id.value,
                        issue.crawl_id.value,
                        _value(issue.page_id) if issue.page_id else None,
                        issue.affected_url.value,
                        issue.issue_type.value,
                        issue.severity.value,
                        issue.explanation,
                    ),
                )

    def save_duplicate_groups(self, crawl_id, groups):
        with self.connection:
            for group in groups:
                self.connection.execute(
                    """
                    INSERT OR REPLACE INTO duplicate_groups(duplicate_group_id, crawl_id, content_hash)
                    VALUES (?, ?, ?)
                    """,
                    (
                        group.duplicate_group_id.value,
                        group.crawl_id.value,
                        group.content_hash.value,
                    ),
                )
                for page_id in group.page_ids:
                    self.connection.execute(
                        """
                        INSERT OR REPLACE INTO duplicate_group_pages(duplicate_group_id, page_id)
                        VALUES (?, ?)
                        """,
                        (group.duplicate_group_id.value, page_id.value),
                    )


class SQLiteResultsReadRepository:
    def __init__(self, connection):
        self.connection = connection

    def list_pages(self, query):
        sql = """
            SELECT page_id, url, final_url, status_code, title, meta_description,
                   canonical_url, word_count, content_type
            FROM pages
            WHERE crawl_id = ?
        """
        rows = self.connection.execute(
            _apply_query_sql(sql, query.options, _PAGE_SORT_FIELDS, "page_id"),
            (_value(query.crawl_id),),
        )
        return tuple(_page_row_from_row(row) for row in rows)

    def list_issues(self, query):
        sql = """
            SELECT issue_id, affected_url, issue_type, severity, explanation, page_id
            FROM issues
            WHERE crawl_id = ?
        """
        rows = self.connection.execute(
            _apply_query_sql(sql, query.options, _ISSUE_SORT_FIELDS, "issue_id"),
            (_value(query.crawl_id),),
        )
        return tuple(_issue_row_from_row(row) for row in rows)

    def list_duplicate_groups(self, query):
        sql = """
            SELECT dg.duplicate_group_id, dg.content_hash, COUNT(dgp.page_id) AS page_count,
                   MIN(p.url) AS representative_url
            FROM duplicate_groups dg
            LEFT JOIN duplicate_group_pages dgp ON dgp.duplicate_group_id = dg.duplicate_group_id
            LEFT JOIN pages p ON p.page_id = dgp.page_id
            WHERE dg.crawl_id = ?
            GROUP BY dg.duplicate_group_id, dg.content_hash
        """
        rows = self.connection.execute(
            _apply_query_sql(
                sql, query.options, _DUPLICATE_SORT_FIELDS, "dg.duplicate_group_id"
            ),
            (_value(query.crawl_id),),
        )
        return tuple(_duplicate_group_row_from_row(row) for row in rows)

    def get_page_detail(self, query):
        page = self.connection.execute(
            """
            SELECT page_id, url, final_url, status_code, title, meta_description,
                   canonical_url, word_count, content_type, content_hash
            FROM pages
            WHERE crawl_id = ? AND page_id = ?
            """,
            (_value(query.crawl_id), _value(query.page_id)),
        ).fetchone()
        if page is None:
            return None
        headings = tuple(
            _heading_from_row(row)
            for row in self.connection.execute(
                "SELECT * FROM headings WHERE page_id = ? ORDER BY position",
                (_value(query.page_id),),
            )
        )
        links = tuple(
            _link_from_row(row)
            for row in self.connection.execute(
                "SELECT * FROM links WHERE source_page_id = ? ORDER BY target_url",
                (_value(query.page_id),),
            )
        )
        redirects = tuple(
            _redirect_from_row(row)
            for row in self.connection.execute(
                "SELECT * FROM redirects WHERE crawl_id = ? ORDER BY from_url, to_url",
                (_value(query.crawl_id),),
            )
        )
        issues = tuple(
            _issue_row_from_row(row)
            for row in self.connection.execute(
                """
                SELECT issue_id, affected_url, issue_type, severity, explanation, page_id
                FROM issues WHERE crawl_id = ? AND page_id = ? ORDER BY issue_type, issue_id
                """,
                (_value(query.crawl_id), _value(query.page_id)),
            )
        )
        return PageDetail(
            page=_page_row_from_row(page),
            headings=headings,
            outlinks=links,
            redirects=redirects,
            content_hash=ContentHash.create(page["content_hash"]).value
            if page["content_hash"]
            else None,
            issues=issues,
        )

    def find_recent_crawl(self):
        row = self.connection.execute(
            "SELECT * FROM crawls ORDER BY created_at DESC, crawl_id DESC LIMIT 1"
        ).fetchone()
        return _crawl_from_row(row) if row else None

    def list_pages_for_export(self, crawl_id):
        return self.list_pages(_query(crawl_id))

    def list_issues_for_export(self, crawl_id):
        return self.list_issues(_query(crawl_id))


class SQLiteExportRepository:
    def __init__(self, connection):
        self.connection = connection

    def save_export(self, export_result):
        self.connection.execute(
            """
            INSERT OR REPLACE INTO exports(
                export_id, crawl_id, kind, target_path, row_count, success, error_code, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                export_result.export_id.value,
                export_result.crawl_id.value,
                export_result.kind.value,
                export_result.target_path.value,
                export_result.row_count,
                int(export_result.success),
                str(export_result.error.code) if export_result.error else None,
                export_result.error.message if export_result.error else None,
            ),
        )
        self.connection.commit()


_PAGE_SORT_FIELDS = {
    "url": "url",
    "final_url": "final_url",
    "status_code": "status_code",
    "title": "title",
    "word_count": "word_count",
    "content_type": "content_type",
}
_ISSUE_SORT_FIELDS = {
    "affected_url": "affected_url",
    "issue_type": "issue_type",
    "severity": "severity",
    "explanation": "explanation",
}
_DUPLICATE_SORT_FIELDS = {
    "content_hash": "dg.content_hash",
    "page_count": "page_count",
    "representative_url": "representative_url",
}


def _query(crawl_id):

    return ResultQuery(crawl_id)


def _apply_query_sql(sql, options=None, allowed_sort_fields=None, tie_breaker="id"):
    options = options or QueryOptions()
    allowed_sort_fields = allowed_sort_fields or {}
    if options.sort_field:
        field = allowed_sort_fields.get(options.sort_field)
        if field is None:
            raise ValueError("Unsupported sort field")
        direction = "DESC" if options.sort_direction == "desc" else "ASC"
        sql += f" ORDER BY {field} {direction}, {tie_breaker} {direction}"
    else:
        sql += f" ORDER BY {tie_breaker} ASC"
    if options.page_size is not None:
        sql += f" LIMIT {int(options.page_size)}"
        if options.offset:
            sql += f" OFFSET {int(options.offset)}"
    elif options.offset:
        sql += f" LIMIT -1 OFFSET {int(options.offset)}"
    return sql


def _crawl_params(crawl):
    return (
        crawl.crawl_id.value,
        crawl.config.start_url.value,
        int(crawl.config.same_host_only),
        crawl.config.page_limit,
        crawl.config.timeout_seconds,
        crawl.status.value,
        _dt(crawl.created_at),
        _dt(crawl.started_at),
        _dt(crawl.completed_at),
        str(crawl.failure.code) if crawl.failure else None,
        crawl.failure.message if crawl.failure else None,
    )


def _page_params(page):
    return (
        page.page_id.value,
        page.crawl_id.value,
        page.url.value,
        page.final_url.value,
        page.status_code,
        page.content_type,
        page.title,
        page.meta_description,
        page.canonical_url.value if page.canonical_url else None,
        page.robots_meta,
        page.word_count.value,
        page.content_length,
        page.content_hash.value if page.content_hash else None,
        page.image_count,
        page.images_missing_alt,
        int(page.has_viewport),
        int(page.has_lang),
        int(page.has_charset),
    )


def _crawl_from_row(row):
    failure = (
        DomainError.of(row["failure_code"], row["failure_message"])
        if row["failure_code"]
        else None
    )
    config = CrawlConfig(
        BaseUrl.create(row["start_url"]).value,
        bool(row["same_host_only"]),
        row["page_limit"],
        row["timeout_seconds"],
    )
    return Crawl(
        CrawlId.create(row["crawl_id"]).value,
        config,
        CrawlStatus(row["status"]),
        _parse_dt(row["created_at"]),
        _parse_dt(row["started_at"]),
        _parse_dt(row["completed_at"]),
        failure,
    )


def _page_from_row(row):
    return ExtractedPage(
        PageId.create(row["page_id"]).value,
        CrawlId.create(row["crawl_id"]).value,
        NormalizedUrl.create(row["url"]).value,
        NormalizedUrl.create(row["final_url"]).value,
        row["status_code"],
        row["content_type"],
        row["title"],
        row["meta_description"],
        NormalizedUrl.create(row["canonical_url"]).value
        if row["canonical_url"]
        else None,
        row["robots_meta"],
        WordCount.create(row["word_count"]).value,
        row["content_length"],
        ContentHash.create(row["content_hash"]).value if row["content_hash"] else None,
        row["image_count"],
        row["images_missing_alt"],
        bool(row["has_viewport"]),
        bool(row["has_lang"]),
        bool(row["has_charset"]),
    )


def _heading_from_row(row):
    return Heading(
        PageId.create(row["page_id"]).value,
        HeadingLevel(row["level"]),
        row["text"],
        row["position"],
    )


def _link_from_row(row):
    return PageLink(
        PageId.create(row["source_page_id"]).value,
        NormalizedUrl.create(row["target_url"]).value,
        LinkRelation(row["relation"]),
        row["anchor_text"],
        bool(row["nofollow"]),
    )


def _redirect_from_row(row):
    return Redirect(
        CrawlId.create(row["crawl_id"]).value,
        NormalizedUrl.create(row["from_url"]).value,
        NormalizedUrl.create(row["to_url"]).value,
        row["status_code"],
    )


def _page_row_from_row(row):
    return PageRow(
        PageId.create(row["page_id"]).value,
        NormalizedUrl.create(row["url"]).value,
        NormalizedUrl.create(row["final_url"]).value,
        row["status_code"],
        row["title"],
        row["meta_description"],
        NormalizedUrl.create(row["canonical_url"]).value
        if row["canonical_url"]
        else None,
        row["word_count"],
        row["content_type"],
    )


def _issue_row_from_row(row):
    return IssueRow(
        IssueId.create(row["issue_id"]).value,
        NormalizedUrl.create(row["affected_url"]).value,
        IssueType(row["issue_type"]),
        IssueSeverity(row["severity"]),
        row["explanation"],
        PageId.create(row["page_id"]).value if row["page_id"] else None,
    )


def _duplicate_group_row_from_row(row):
    return DuplicateGroupRow(
        DuplicateGroupId.create(row["duplicate_group_id"]).value,
        ContentHash.create(row["content_hash"]).value,
        row["page_count"],
        NormalizedUrl.create(row["representative_url"]).value
        if row["representative_url"]
        else None,
    )


def _dt(value):
    return value.isoformat() if value else None


def _parse_dt(value):
    return datetime.fromisoformat(value) if value else None


def _value(value):
    return getattr(value, "value", value)
