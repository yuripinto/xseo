from hypothesis import given
from hypothesis import strategies as st

from tests.strategies.domain import (
    html_documents_with_links,
    malformed_html_fragments,
    visible_text_variants,
)
from xseo.domain.entities import FetchResult
from xseo.domain.enums import FetchStatus
from xseo.domain.extraction import (
    SeoExtractionPipeline,
    content_hash_for_text,
    word_count,
)
from xseo.domain.ids import CrawlId, PageId
from xseo.domain.urls import NormalizedUrl


def _fetch(html):
    url = NormalizedUrl.create("https://example.com/").value
    return FetchResult(
        requested_url=url,
        final_url=url,
        status=FetchStatus.SUCCESS,
        status_code=200,
        content_type="text/html",
        body=html.encode("utf-8", errors="replace"),
    )


def _ids():
    return CrawlId.create("crawl-property").value, PageId.create("page-property").value


@given(html_documents_with_links())
def test_extracted_links_are_not_empty_or_fragment_only(html):
    crawl_id, page_id = _ids()
    output = SeoExtractionPipeline().extract(_fetch(html), crawl_id, page_id)

    for link in output.raw_links:
        assert link.raw_href.strip()
        assert not link.raw_href.strip().startswith("#")


@given(st.text())
def test_word_count_is_never_negative(text):
    assert word_count(text) >= 0


@given(visible_text_variants())
def test_content_hash_is_stable_for_equivalent_normalized_text(pair):
    first, second = pair

    assert content_hash_for_text(first) == content_hash_for_text(second)


@given(malformed_html_fragments())
def test_metadata_extraction_tolerates_malformed_html(html):
    crawl_id, page_id = _ids()
    output = SeoExtractionPipeline().extract(_fetch(html), crawl_id, page_id)

    assert output.extraction_result is not None
