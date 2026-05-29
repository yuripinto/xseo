from xseo.domain.entities import FetchResult
from xseo.domain.enums import FetchStatus, HeadingLevel
from xseo.domain.extraction import SeoExtractionPipeline
from xseo.domain.ids import CrawlId, PageId
from xseo.domain.urls import NormalizedUrl


def _ids():
    return CrawlId.create("crawl-1").value, PageId.create("page-1").value


def _url(value="https://example.com/"):
    return NormalizedUrl.create(value).value


def _fetch(body, content_type="text/html; charset=utf-8"):
    url = _url()
    return FetchResult(
        requested_url=url,
        final_url=url,
        status=FetchStatus.SUCCESS,
        status_code=200,
        content_type=content_type,
        body=body,
    )


def test_extraction_pipeline_extracts_metadata_headings_links_and_hash():
    crawl_id, page_id = _ids()
    html = b"""
    <html>
      <head>
        <title>Example title</title>
        <meta name="description" content="Example description">
        <meta name="robots" content="noindex">
        <link rel="canonical" href="/canonical">
      </head>
      <body>
        <h1>Main heading</h1>
        <h2>Sub heading</h2>
        <a href="/next" rel="nofollow">Next page</a>
        <a href="#local">Local</a>
        <script>hidden()</script>
        Visible content here.
      </body>
    </html>
    """

    output = SeoExtractionPipeline().extract(_fetch(html), crawl_id, page_id)

    page = output.extraction_result.page
    assert page.title == "Example title"
    assert page.meta_description == "Example description"
    assert page.robots_meta == "noindex"
    assert page.canonical_url.value == "https://example.com/canonical"
    assert page.word_count.value >= 5
    assert page.content_hash.value
    assert [heading.level for heading in output.extraction_result.headings] == [
        HeadingLevel.H1,
        HeadingLevel.H2,
    ]
    assert len(output.raw_links) == 1
    assert output.raw_links[0].raw_href == "/next"
    assert output.raw_links[0].nofollow


def test_extraction_pipeline_counts_images_missing_alt():
    crawl_id, page_id = _ids()
    html = b"""
    <html><body>
      <img src="/described.png" alt="A described image">
      <img src="/missing.png">
      <img src="/decorative.png" alt="">
    </body></html>
    """

    output = SeoExtractionPipeline().extract(_fetch(html), crawl_id, page_id)

    page = output.extraction_result.page
    assert page.image_count == 3
    assert page.images_missing_alt == 1


def test_extraction_pipeline_returns_error_for_non_html_success():
    crawl_id, page_id = _ids()

    output = SeoExtractionPipeline().extract(
        _fetch(b"{}", "application/json"), crawl_id, page_id
    )

    assert output.extraction_result.page is None
    assert output.extraction_result.error.code == "extraction.not_html"


def test_extraction_pipeline_decodes_invalid_utf8_with_replacement():
    crawl_id, page_id = _ids()

    output = SeoExtractionPipeline().extract(
        _fetch(b"<html><body>\xff</body></html>"), crawl_id, page_id
    )

    assert output.extraction_result.page is not None


def test_extraction_pipeline_tolerates_malformed_html():
    crawl_id, page_id = _ids()

    output = SeoExtractionPipeline().extract(
        _fetch(b"<html><title>Broken<body><h1>X"), crawl_id, page_id
    )

    assert output.extraction_result.error is None
