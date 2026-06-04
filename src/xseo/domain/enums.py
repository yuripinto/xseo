"""Stable domain enumerations."""

from enum import StrEnum


class CrawlStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    COMPLETED = "completed"
    FAILED = "failed"


class FetchStatus(StrEnum):
    SUCCESS = "success"
    REDIRECT = "redirect"
    TIMEOUT = "timeout"
    NETWORK_ERROR = "network_error"
    INVALID_RESPONSE = "invalid_response"
    UNSUPPORTED_CONTENT = "unsupported_content"


class IssueSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class IssueType(StrEnum):
    BROKEN_INTERNAL_LINK = "broken_internal_link"
    REDIRECTING_URL = "redirecting_url"
    REDIRECT_CHAIN = "redirect_chain"
    REDIRECT_LOOP = "redirect_loop"
    TITLE_MISSING = "title_missing"
    TITLE_DUPLICATE = "title_duplicate"
    TITLE_TOO_SHORT = "title_too_short"
    TITLE_TOO_LONG = "title_too_long"
    META_DESCRIPTION_MISSING = "meta_description_missing"
    META_DESCRIPTION_DUPLICATE = "meta_description_duplicate"
    META_DESCRIPTION_TOO_SHORT = "meta_description_too_short"
    META_DESCRIPTION_TOO_LONG = "meta_description_too_long"
    H1_MISSING = "h1_missing"
    H1_MULTIPLE = "h1_multiple"
    CANONICAL_MISMATCH = "canonical_mismatch"
    CANONICAL_TO_NOINDEX = "canonical_to_noindex"
    CANONICAL_TO_REDIRECT = "canonical_to_redirect"
    CANONICAL_CROSS_DOMAIN = "canonical_cross_domain"
    THIN_CONTENT = "thin_content"
    EXACT_DUPLICATE = "exact_duplicate"
    PAGE_TOO_LARGE = "page_too_large"
    NOINDEX_PAGE = "noindex_page"
    INSECURE_INTERNAL_LINK = "insecure_internal_link"
    INTERNAL_LINK_NOFOLLOW = "internal_link_nofollow"
    EXCESSIVE_LINKS = "excessive_links"
    IMAGES_MISSING_ALT = "images_missing_alt"
    MISSING_VIEWPORT = "missing_viewport"
    MISSING_LANG = "missing_lang"
    MISSING_CHARSET = "missing_charset"
    MIXED_CONTENT = "mixed_content"
    OPEN_GRAPH_MISSING = "open_graph_missing"
    STRUCTURED_DATA_MISSING = "structured_data_missing"
    HREFLANG_NO_SELF_REFERENCE = "hreflang_no_self_reference"
    SITEMAP_MISSING = "sitemap_missing"
    PAGE_MISSING_FROM_SITEMAP = "page_missing_from_sitemap"
    SITEMAP_STALE_URL = "sitemap_stale_url"


class HeadingLevel(StrEnum):
    H1 = "h1"
    H2 = "h2"
    H3 = "h3"


class LinkRelation(StrEnum):
    INTERNAL = "internal"
    EXTERNAL = "external"


class ExportKind(StrEnum):
    PAGES = "pages"
    ISSUES = "issues"
