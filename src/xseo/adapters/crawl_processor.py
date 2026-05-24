"""Page processing adapter: extracts SEO data and saves pages during link discovery."""

from __future__ import annotations

from datetime import UTC, datetime

from xseo.domain.extraction.pipeline import SeoExtractionPipeline
from xseo.domain.ids import PageId


class PageProcessorLinkDiscovery:
    """Satisfies the LinkDiscoveryPort while extracting and persisting each page."""

    def __init__(
        self,
        extraction_pipeline: SeoExtractionPipeline,
        data_repository: object,
        crawl_id: object,
        page_id_factory: object | None = None,
    ) -> None:
        self.extraction_pipeline = extraction_pipeline
        self.data_repository = data_repository
        self.crawl_id = crawl_id
        self.page_id_factory = page_id_factory or _default_page_id

    def discover_links(self, fetch_result: object) -> tuple:
        page_id = self.page_id_factory()
        output = self.extraction_pipeline.extract(fetch_result, self.crawl_id, page_id)
        if output.extraction_result.page is not None:
            page = output.extraction_result.page
            self.data_repository.save_page(page)
            self.data_repository.save_headings(page.page_id, output.extraction_result.headings)
            for redirect in getattr(fetch_result, "redirect_chain", ()):
                self.data_repository.save_redirect(redirect)
        return output.raw_links


def _default_page_id() -> object:
    ts = datetime.now(UTC).isoformat().replace(":", "-").replace("+", "")
    return PageId.create(f"page-{ts}").value
