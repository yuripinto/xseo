"""SEO issue analysis domain services."""

from xseo.domain.analysis.cross_page_detectors import (
    detect_cross_page_issues,
    detect_duplicate_meta_description_issues,
    detect_duplicate_title_issues,
)
from xseo.domain.analysis.keys import (
    duplicate_group_key,
    issue_key,
    normalize_comparable_text,
)
from xseo.domain.analysis.link_detectors import (
    LinkStatusRecord,
    detect_excessive_link_issues,
    detect_insecure_link_issues,
    detect_link_issues,
    detect_nofollow_internal_link_issues,
    detect_redirect_chain_issues,
)
from xseo.domain.analysis.page_detectors import detect_page_issues
from xseo.domain.analysis.policies import (
    DEFAULT_SEVERITY_POLICY,
    DEFAULT_THRESHOLDS,
    IssueSeverityPolicy,
    ThresholdPolicy,
)
from xseo.domain.analysis.service import IssueAnalysisService

__all__ = [
    "DEFAULT_SEVERITY_POLICY",
    "DEFAULT_THRESHOLDS",
    "IssueAnalysisService",
    "IssueSeverityPolicy",
    "LinkStatusRecord",
    "ThresholdPolicy",
    "detect_cross_page_issues",
    "detect_duplicate_meta_description_issues",
    "detect_duplicate_title_issues",
    "detect_excessive_link_issues",
    "detect_insecure_link_issues",
    "detect_link_issues",
    "detect_nofollow_internal_link_issues",
    "detect_page_issues",
    "detect_redirect_chain_issues",
    "duplicate_group_key",
    "issue_key",
    "normalize_comparable_text",
]
