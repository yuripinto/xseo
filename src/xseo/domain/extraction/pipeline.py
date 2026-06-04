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
            final_url = fetch_result.final_url or fetch_result.requested_url
            canonical = _canonical_url(tree, final_url, self.normalizer)
            image_count, images_missing_alt, images_missing_dimensions = _image_stats(
                tree
            )
            has_viewport = _has_meta(tree, "viewport")
            has_lang = _has_lang(tree)
            has_charset = _has_charset(tree)
            has_open_graph = _has_open_graph(tree)
            has_structured_data = _has_structured_data(tree)
            mixed_content_count = _mixed_content_count(tree, final_url)
            has_hreflang, hreflang_self_referential = _hreflang_stats(
                tree, final_url, self.normalizer
            )
            # _visible_text strips <script>/<style> nodes, so it must run only
            # after the signals above that inspect those tags.
            visible_text = _visible_text(tree)

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
                image_count=image_count,
                images_missing_alt=images_missing_alt,
                has_viewport=has_viewport,
                has_lang=has_lang,
                has_charset=has_charset,
                has_open_graph=has_open_graph,
                has_structured_data=has_structured_data,
                mixed_content_count=mixed_content_count,
                has_hreflang=has_hreflang,
                hreflang_self_referential=hreflang_self_referential,
                images_missing_dimensions=images_missing_dimensions,
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


def _image_stats(tree):
    images = tree.css("img")
    missing_alt = sum(1 for image in images if "alt" not in image.attributes)
    # Missing an explicit width/height lets the image reflow as it loads,
    # causing layout shift (CLS). Either dimension absent counts.
    missing_dimensions = sum(
        1
        for image in images
        if not _has_dimension(image, "width") or not _has_dimension(image, "height")
    )
    return len(images), missing_alt, missing_dimensions


def _has_dimension(image, attr):
    value = image.attributes.get(attr)
    return value is not None and value.strip() != ""


def _has_meta(tree, name):
    node = tree.css_first(f'meta[name="{name}"]')
    if node is None:
        node = tree.css_first(f'meta[name="{name.capitalize()}"]')
    return node is not None


def _has_lang(tree):
    node = tree.css_first("html")
    lang = node.attributes.get("lang") if node is not None else None
    return bool(lang and lang.strip())


def _has_charset(tree):
    if tree.css_first("meta[charset]") is not None:
        return True
    node = tree.css_first('meta[http-equiv="Content-Type"]')
    if node is None:
        node = tree.css_first('meta[http-equiv="content-type"]')
    content = (node.attributes.get("content") or "") if node is not None else ""
    return "charset" in content.lower()


def _hreflang_stats(tree, final_url, normalizer):
    """Return (has_hreflang, self_referential) for the page's hreflang set.

    Google requires every hreflang cluster to be self-referential — a page that
    declares language alternates must also list its own URL among them. We
    normalize each ``href`` against the page URL and check the page's own final
    URL is present.
    """
    nodes = tree.css('link[rel="alternate"][hreflang]')
    if not nodes:
        return False, True
    own = final_url.value if hasattr(final_url, "value") else str(final_url)
    self_referential = False
    for node in nodes:
        href = node.attributes.get("href")
        if not href:
            continue
        result = normalizer.normalize(href, base_url=final_url)
        if result.ok and result.value.value == own:
            self_referential = True
            break
    return True, self_referential


def _has_open_graph(tree):
    # og:title is the minimum signal that Open Graph cards are configured.
    return tree.css_first('meta[property="og:title"]') is not None


def _has_structured_data(tree):
    # JSON-LD is the dominant structured-data format; microdata is rarer and
    # noisier to detect, so we treat a JSON-LD block as the signal.
    return tree.css_first('script[type="application/ld+json"]') is not None


# Sub-resource references that load content into the page; an http:// URL here
# on an https page is mixed content the browser may block or warn about.
_MIXED_CONTENT_SELECTORS = (
    ("img", "src"),
    ("script", "src"),
    ("iframe", "src"),
    ("audio", "src"),
    ("video", "src"),
    ("source", "src"),
    ('link[rel="stylesheet"]', "href"),
)


def _mixed_content_count(tree, final_url):
    base = final_url.value if hasattr(final_url, "value") else str(final_url)
    if not base.lower().startswith("https://"):
        return 0
    count = 0
    for selector, attr in _MIXED_CONTENT_SELECTORS:
        for node in tree.css(selector):
            value = (node.attributes.get(attr) or "").strip().lower()
            if value.startswith("http://"):
                count += 1
    return count


def _visible_text(tree):
    for node in tree.css("script,style"):
        node.decompose()
    body = tree.body
    node = body if body is not None else tree.root
    return normalize_visible_text(node.text(separator=" "))
