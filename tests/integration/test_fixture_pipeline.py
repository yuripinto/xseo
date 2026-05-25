import csv
from datetime import UTC, datetime
from pathlib import Path

from xseo.adapters.export import CsvExportAdapter
from xseo.adapters.persistence import (
    SQLiteAnalysisRepository,
    SQLiteCrawlDataRepository,
    SQLiteCrawlRepository,
    SQLiteDatabase,
    SQLiteExportRepository,
    SQLiteResultsReadRepository,
)
from xseo.application import ExportCommand, ResultQuery
from xseo.application.services import (
    ExportApplicationService,
    ResultsApplicationService,
)
from xseo.domain.analysis import IssueAnalysisService
from xseo.domain.duplicates import detect_duplicate_groups
from xseo.domain.entities import Crawl, CrawlConfig, FetchResult
from xseo.domain.enums import ExportKind, FetchStatus, IssueType
from xseo.domain.extraction import SeoExtractionPipeline
from xseo.domain.ids import CrawlId, PageId
from xseo.domain.urls import BaseUrl, NormalizedUrl

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "site"


def _id(cls, value):
    return cls.create(value).value


def _url(value):
    return NormalizedUrl.create(value).value


def _fetch(path, url):
    return FetchResult(
        requested_url=_url(url),
        final_url=_url(url),
        status=FetchStatus.SUCCESS,
        status_code=200,
        content_type="text/html; charset=utf-8",
        body=(FIXTURES / path).read_bytes(),
    )


def test_fixture_pipeline_persists_reads_and_exports(tmp_path):
    conn = SQLiteDatabase.memory().connect()
    crawl_id = _id(CrawlId, "crawl-fixture")
    crawl = Crawl.create(
        crawl_id,
        CrawlConfig.create(BaseUrl.create("https://example.com/").value).value,
        datetime(2026, 1, 1, tzinfo=UTC),
    )
    crawl_repo = SQLiteCrawlRepository(conn)
    data_repo = SQLiteCrawlDataRepository(conn)
    analysis_repo = SQLiteAnalysisRepository(conn)
    read_repo = SQLiteResultsReadRepository(conn)
    results_service = ResultsApplicationService(read_repo)
    export_service = ExportApplicationService(
        read_repo, CsvExportAdapter(), SQLiteExportRepository(conn)
    )
    extractor = SeoExtractionPipeline()
    extracted = []

    crawl_repo.save_crawl(crawl)
    for index, (fixture, url) in enumerate(
        (
            ("index.html", "https://example.com/"),
            ("duplicate.html", "https://example.com/duplicate"),
            ("missing-title.html", "https://example.com/missing-title"),
        ),
        start=1,
    ):
        output = extractor.extract(
            _fetch(fixture, url), crawl_id, _id(PageId, f"page-{index}")
        )
        page = output.extraction_result.page
        extracted.append(page)
        data_repo.save_page(page)
        data_repo.save_headings(page.page_id, output.extraction_result.headings)

    issues = IssueAnalysisService().detect_issues(
        crawl_id, tuple(extracted), data_repo.load_analysis_data(crawl_id).headings
    )
    duplicate_groups = detect_duplicate_groups(crawl_id, tuple(extracted))
    analysis_repo.save_issues(crawl_id, issues)
    analysis_repo.save_duplicate_groups(crawl_id, duplicate_groups)

    pages = results_service.list_pages(ResultQuery(crawl_id))
    issue_rows = results_service.list_issues(ResultQuery(crawl_id))
    groups = results_service.list_duplicate_groups(ResultQuery(crawl_id))
    export = export_service.export(
        ExportCommand(crawl_id, ExportKind.PAGES, tmp_path / "pages.csv")
    )

    with (tmp_path / "pages.csv").open(newline="", encoding="utf-8") as handle:
        exported_pages = list(csv.DictReader(handle))
    assert pages.success and len(pages.value) == 3
    assert issue_rows.success
    assert any(row.issue_type == IssueType.TITLE_MISSING for row in issue_rows.value)
    assert groups.success and groups.value[0].page_count == 2
    assert export.success and export.value.row_count == 3
    assert len(exported_pages) == 3
