"""SEO metadata extraction pipeline."""

from __future__ import annotations

from selectolax.parser import HTMLParser

from xseo.domain.entities import ExtractedPage, ExtractionResult, Heading
from xseo.domain.enums import FetchStatus, HeadingLevel
from xseo.domain.errors import DomainError
from xseo.domain.extraction.hashing import content_hash_for_text
from xseo.domain.extraction.links import extract_raw_links
from xseo.domain.extraction.results import SeoExtractionOutput
from xseo.domain.extraction.text import normalize_visible_text, word_count
from xseo.domain.frontier import UrlNormalizer
from xseo.domain.value_objects import WordCount


class SeoExtractionPipeline:
    def __init__(self, normalizer=None):
        self.normalizer = normalizer or UrlNormalizer()

    def extract(self, fetch_result, crawl_id, page_id, encoding=None):
        try:
            if fetch_result.status != FetchStatus.SUCCESS or not _is_html(
                fetch_result.content_type
            ):
                return SeoExtractionOutput(
                    ExtractionResult(
                        page=None,
                        error=DomainError.of(
                            "extraction.not_html", "Fetch result is not successful HTML"
                        ),
                    )
                )

            body = fetch_result.body or b""
            html = _decode_body(body, encoding)
            tree = HTMLParser(html)
            visible_text = _visible_text(tree)
            final_url = fetch_result.final_url or fetch_result.requested_url
            canonical = _canonical_url(tree, final_url, self.normalizer)

            page = ExtractedPage(
                page_id=page_id,
                crawl_id=crawl_id,
                url=fetch_result.requested_url,
                final_url=final_url,
                status_code=fetch_result.status_code or 0,
                content_type=fetch_result.content_type,
                title=_text_of(tree.css_first("title")),
                meta_description=_meta_content(tree, "description"),
                canonical_url=canonical,
                robots_meta=_meta_content(tree, "robots"),
                word_count=WordCount.create(word_count(visible_text)).value,
                content_length=len(body),
                content_hash=content_hash_for_text(visible_text),
            )
            headings = _headings(tree, page_id)
            links = extract_raw_links(tree, final_url)
            return SeoExtractionOutput(
                extraction_result=ExtractionResult(page=page, headings=headings),
                raw_links=links,
            )
        except Exception as exc:
            return SeoExtractionOutput(
                ExtractionResult(
                    page=None,
                    error=DomainError.of("extraction.failed", str(exc)),
                )
            )


def _decode_body(body, encoding):
    selected = encoding or "utf-8"
    return body.decode(selected, errors="replace")


def _is_html(content_type):
    return "html" in (content_type or "").lower()


def _text_of(node):
    if node is None:
        return None
    text = normalize_visible_text(node.text())
    return text or None


def _meta_content(tree, name):
    node = tree.css_first(f'meta[name="{name}"]')
    if node is None:
        node = tree.css_first(f'meta[name="{name.capitalize()}"]')
    if node is None:
        return None
    content = normalize_visible_text(node.attributes.get("content"))
    return content or None


def _canonical_url(tree, base_url, normalizer):
    node = tree.css_first('link[rel="canonical"]')
    if node is None:
        return None
    href = node.attributes.get("href")
    result = normalizer.normalize(href, base_url=base_url)
    return result.value if result.ok else None


def _headings(tree, page_id):
    headings = []
    for selector, level in (
        ("h1", HeadingLevel.H1),
        ("h2", HeadingLevel.H2),
        ("h3", HeadingLevel.H3),
    ):
        for node in tree.css(selector):
            text = normalize_visible_text(node.text())
            if text:
                headings.append(
                    Heading(
                        page_id=page_id,
                        level=level,
                        text=text,
                        position=len(headings),
                    )
                )
    return tuple(headings)


def _visible_text(tree):
    for node in tree.css("script,style"):
        node.decompose()
    body = tree.body
    node = body if body is not None else tree.root
    return normalize_visible_text(node.text(separator=" "))
