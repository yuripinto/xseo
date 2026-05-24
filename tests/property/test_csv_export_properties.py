import csv
from tempfile import TemporaryDirectory

from hypothesis import given
from hypothesis import strategies as st

from xseo.adapters.export import CsvExportAdapter
from xseo.application.read_models import PageRow
from xseo.domain.ids import CrawlId, PageId
from xseo.domain.urls import NormalizedUrl


def _id(cls, value):
    return cls.create(value).value


def _url(value):
    return NormalizedUrl.create(value).value


@given(st.lists(st.integers(min_value=0, max_value=999), min_size=0, max_size=20))
def test_pages_csv_row_count_matches_export_result(values):
    rows = tuple(
        PageRow(
            _id(PageId, f"page-{index}"),
            _url(f"https://example.com/{value}"),
            _url(f"https://example.com/{value}"),
            200,
            f"Title {value}",
            "",
            None,
            value,
            "text/html",
        )
        for index, value in enumerate(values)
    )
    with TemporaryDirectory() as directory:
        path = f"{directory}/pages.csv"
        result = CsvExportAdapter(_id(CrawlId, "crawl-1")).write_pages(path, rows)
        with open(path, newline="", encoding="utf-8") as handle:
            exported_rows = list(csv.DictReader(handle))
    assert result.row_count == len(values)
    assert len(exported_rows) == len(values)
