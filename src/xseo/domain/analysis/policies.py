"""SEO analysis policies and threshold defaults."""

from __future__ import annotations

from dataclasses import dataclass, field

from xseo.domain.enums import IssueSeverity, IssueType


@dataclass(frozen=True)
class ThresholdPolicy:
    title_min: int = 30
    title_max: int = 60
    meta_description_min: int = 70
    meta_description_max: int = 160
    thin_content_min_words: int = 200
    page_size_max_bytes: int = 2_000_000
    max_links_per_page: int = 300
    max_crawl_depth: int = 4


@dataclass(frozen=True)
class IssueSeverityPolicy:
    severities: dict[IssueType, IssueSeverity] = field(
        default_factory=lambda: {
            IssueType.BROKEN_INTERNAL_LINK: IssueSeverity.HIGH,
            IssueType.REDIRECTING_URL: IssueSeverity.LOW,
            IssueType.REDIRECT_CHAIN: IssueSeverity.MEDIUM,
            IssueType.REDIRECT_LOOP: IssueSeverity.HIGH,
            IssueType.TITLE_MISSING: IssueSeverity.MEDIUM,
            IssueType.TITLE_DUPLICATE: IssueSeverity.MEDIUM,
            IssueType.TITLE_TOO_SHORT: IssueSeverity.LOW,
            IssueType.TITLE_TOO_LONG: IssueSeverity.LOW,
            IssueType.META_DESCRIPTION_MISSING: IssueSeverity.MEDIUM,
            IssueType.META_DESCRIPTION_DUPLICATE: IssueSeverity.MEDIUM,
            IssueType.META_DESCRIPTION_TOO_SHORT: IssueSeverity.LOW,
            IssueType.META_DESCRIPTION_TOO_LONG: IssueSeverity.LOW,
            IssueType.H1_MISSING: IssueSeverity.MEDIUM,
            IssueType.H1_MULTIPLE: IssueSeverity.MEDIUM,
            IssueType.CANONICAL_MISMATCH: IssueSeverity.HIGH,
            IssueType.CANONICAL_TO_NOINDEX: IssueSeverity.HIGH,
            IssueType.CANONICAL_TO_REDIRECT: IssueSeverity.MEDIUM,
            IssueType.CANONICAL_CROSS_DOMAIN: IssueSeverity.MEDIUM,
            IssueType.THIN_CONTENT: IssueSeverity.LOW,
            IssueType.PAGE_TOO_DEEP: IssueSeverity.LOW,
            IssueType.EXACT_DUPLICATE: IssueSeverity.MEDIUM,
            IssueType.PAGE_TOO_LARGE: IssueSeverity.LOW,
            IssueType.NOINDEX_PAGE: IssueSeverity.MEDIUM,
            IssueType.INSECURE_INTERNAL_LINK: IssueSeverity.MEDIUM,
            IssueType.INTERNAL_LINK_NOFOLLOW: IssueSeverity.LOW,
            IssueType.EXCESSIVE_LINKS: IssueSeverity.LOW,
            IssueType.IMAGES_MISSING_ALT: IssueSeverity.LOW,
            IssueType.MISSING_VIEWPORT: IssueSeverity.MEDIUM,
            IssueType.MISSING_LANG: IssueSeverity.LOW,
            IssueType.MISSING_CHARSET: IssueSeverity.LOW,
            IssueType.MIXED_CONTENT: IssueSeverity.HIGH,
            IssueType.OPEN_GRAPH_MISSING: IssueSeverity.LOW,
            IssueType.STRUCTURED_DATA_MISSING: IssueSeverity.LOW,
            IssueType.HREFLANG_NO_SELF_REFERENCE: IssueSeverity.MEDIUM,
            IssueType.SITEMAP_MISSING: IssueSeverity.LOW,
            IssueType.PAGE_MISSING_FROM_SITEMAP: IssueSeverity.LOW,
            IssueType.SITEMAP_STALE_URL: IssueSeverity.LOW,
            IssueType.ORPHAN_PAGE: IssueSeverity.MEDIUM,
        }
    )

    def severity_for(self, issue_type):
        return self.severities[issue_type]


DEFAULT_THRESHOLDS = ThresholdPolicy()
DEFAULT_SEVERITY_POLICY = IssueSeverityPolicy()
