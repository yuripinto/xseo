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


def test_extraction_pipeline_counts_images_missing_dimensions():
    crawl_id, page_id = _ids()
    html = b"""
    <html><body>
      <img src="/sized.png" width="200" height="100" alt="sized">
      <img src="/width-only.png" width="200" alt="partial">
      <img src="/none.png" alt="none">
      <img src="/empty.png" width="" height="" alt="empty">
    </body></html>
    """

    output = SeoExtractionPipeline().extract(_fetch(html), crawl_id, page_id)

    page = output.extraction_result.page
    assert page.image_count == 4
    # Only the fully-sized image is exempt; the other three lack a usable dimension.
    assert page.images_missing_dimensions == 3


def test_extraction_pipeline_detects_head_meta_presence():
    crawl_id, page_id = _ids()
    present = b"""
    <html lang="en"><head>
      <meta charset="utf-8">
      <meta name="viewport" content="width=device-width, initial-scale=1">
    </head><body>Hi</body></html>
    """
    absent = b"<html><head></head><body>Hi</body></html>"

    with_meta = (
        SeoExtractionPipeline().extract(_fetch(present), crawl_id, page_id)
    ).extraction_result.page
    without_meta = (
        SeoExtractionPipeline().extract(_fetch(absent), crawl_id, page_id)
    ).extraction_result.page

    assert (with_meta.has_viewport, with_meta.has_lang, with_meta.has_charset) == (
        True,
        True,
        True,
    )
    assert (
        without_meta.has_viewport,
        without_meta.has_lang,
        without_meta.has_charset,
    ) == (False, False, False)


def test_extraction_pipeline_detects_open_graph_and_structured_data():
    crawl_id, page_id = _ids()
    rich = b"""
    <html><head>
      <meta property="og:title" content="Shareable">
      <script type="application/ld+json">{"@type":"Article"}</script>
    </head><body>Hi</body></html>
    """
    bare = b"<html><head></head><body>Hi</body></html>"

    rich_page = (
        SeoExtractionPipeline().extract(_fetch(rich), crawl_id, page_id)
    ).extraction_result.page
    bare_page = (
        SeoExtractionPipeline().extract(_fetch(bare), crawl_id, page_id)
    ).extraction_result.page

    assert (rich_page.has_open_graph, rich_page.has_structured_data) == (True, True)
    assert (bare_page.has_open_graph, bare_page.has_structured_data) == (False, False)


def test_extraction_pipeline_flags_invalid_structured_data():
    crawl_id, page_id = _ids()
    broken = b"""
    <html><head>
      <script type="application/ld+json">{"@type": "Article",}</script>
    </head><body>Hi</body></html>
    """
    valid = b"""
    <html><head>
      <script type="application/ld+json">
        {"@context": "https://schema.org", "@type": "Article"}
      </script>
    </head><body>Hi</body></html>
    """

    broken_page = (
        SeoExtractionPipeline().extract(_fetch(broken), crawl_id, page_id)
    ).extraction_result.page
    valid_page = (
        SeoExtractionPipeline().extract(_fetch(valid), crawl_id, page_id)
    ).extraction_result.page

    assert broken_page.has_structured_data is True
    assert broken_page.structured_data_invalid is True
    assert valid_page.structured_data_invalid is False


def test_extraction_pipeline_counts_mixed_content_only_on_https():
    crawl_id, page_id = _ids()
    body = b"""
    <html><head>
      <link rel="stylesheet" href="http://cdn.example.com/app.css">
    </head><body>
      <img src="http://cdn.example.com/a.png">
      <script src="https://cdn.example.com/safe.js"></script>
      <img src="/relative.png">
    </body></html>
    """

    # Same markup served from https counts the two http sub-resources...
    https_url = NormalizedUrl.create("https://example.com/").value
    https_page = (
        SeoExtractionPipeline().extract(
            FetchResult(
                requested_url=https_url,
                final_url=https_url,
                status=FetchStatus.SUCCESS,
                status_code=200,
                content_type="text/html",
                body=body,
            ),
            crawl_id,
            page_id,
        )
    ).extraction_result.page
    assert https_page.mixed_content_count == 2

    # ...but on an http page there is no mixed content to flag.
    http_url = NormalizedUrl.create("http://example.com/").value
    http_page = (
        SeoExtractionPipeline().extract(
            FetchResult(
                requested_url=http_url,
                final_url=http_url,
                status=FetchStatus.SUCCESS,
                status_code=200,
                content_type="text/html",
                body=body,
            ),
            crawl_id,
            page_id,
        )
    ).extraction_result.page
    assert http_page.mixed_content_count == 0


def test_extraction_pipeline_detects_hreflang_self_reference():
    crawl_id, page_id = _ids()
    # The page is https://example.com/ and lists itself among the alternates.
    good = b"""
    <html><head>
      <link rel="alternate" hreflang="en" href="https://example.com/">
      <link rel="alternate" hreflang="es" href="https://example.com/es/">
    </head><body>Hi</body></html>
    """
    # Same alternates but the page omits its own URL.
    missing = b"""
    <html><head>
      <link rel="alternate" hreflang="es" href="https://example.com/es/">
      <link rel="alternate" hreflang="fr" href="https://example.com/fr/">
    </head><body>Hi</body></html>
    """
    none = b"<html><head></head><body>Hi</body></html>"

    good_page = (
        SeoExtractionPipeline().extract(_fetch(good), crawl_id, page_id)
    ).extraction_result.page
    missing_page = (
        SeoExtractionPipeline().extract(_fetch(missing), crawl_id, page_id)
    ).extraction_result.page
    none_page = (
        SeoExtractionPipeline().extract(_fetch(none), crawl_id, page_id)
    ).extraction_result.page

    assert (good_page.has_hreflang, good_page.hreflang_self_referential) == (True, True)
    assert (missing_page.has_hreflang, missing_page.hreflang_self_referential) == (
        True,
        False,
    )
    assert (none_page.has_hreflang, none_page.hreflang_self_referential) == (
        False,
        True,
    )


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
