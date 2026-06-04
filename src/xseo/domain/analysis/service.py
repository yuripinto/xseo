"""Issue analysis orchestration service."""

from __future__ import annotations

from xseo.domain.analysis.cross_page_detectors import (
    detect_canonical_target_issues,
    detect_cross_page_issues,
)
from xseo.domain.analysis.link_detectors import (
    detect_excessive_link_issues,
    detect_insecure_link_issues,
    detect_link_issues,
    detect_nofollow_internal_link_issues,
    detect_redirect_chain_issues,
)
from xseo.domain.analysis.page_detectors import detect_page_issues
from xseo.domain.analysis.policies import DEFAULT_SEVERITY_POLICY, DEFAULT_THRESHOLDS


class IssueAnalysisService:
    def __init__(
        self, thresholds=DEFAULT_THRESHOLDS, severity_policy=DEFAULT_SEVERITY_POLICY
    ):
        self.thresholds = thresholds
        self.severity_policy = severity_policy

    def detect_issues(
        self,
        crawl_id,
        pages,
        headings=(),
        link_statuses=(),
        links=(),
        redirects=(),
    ):
        seen = set()
        issues = []

        for page in pages:
            for issue in detect_page_issues(
                page,
                headings,
                self.thresholds,
                self.severity_policy,
            ):
                if issue.issue_id.value not in seen:
                    seen.add(issue.issue_id.value)
                    issues.append(issue)

        for issue in detect_cross_page_issues(pages, self.severity_policy):
            if issue.issue_id.value not in seen:
                seen.add(issue.issue_id.value)
                issues.append(issue)

        for issue in detect_canonical_target_issues(pages, self.severity_policy):
            if issue.issue_id.value not in seen:
                seen.add(issue.issue_id.value)
                issues.append(issue)

        for issue in detect_link_issues(crawl_id, link_statuses, self.severity_policy):
            if issue.issue_id.value not in seen:
                seen.add(issue.issue_id.value)
                issues.append(issue)

        for issue in detect_insecure_link_issues(pages, links, self.severity_policy):
            if issue.issue_id.value not in seen:
                seen.add(issue.issue_id.value)
                issues.append(issue)

        for issue in detect_redirect_chain_issues(
            crawl_id, redirects, self.severity_policy
        ):
            if issue.issue_id.value not in seen:
                seen.add(issue.issue_id.value)
                issues.append(issue)

        for issue in detect_nofollow_internal_link_issues(
            pages, links, self.severity_policy
        ):
            if issue.issue_id.value not in seen:
                seen.add(issue.issue_id.value)
                issues.append(issue)

        for issue in detect_excessive_link_issues(
            pages, links, self.thresholds, self.severity_policy
        ):
            if issue.issue_id.value not in seen:
                seen.add(issue.issue_id.value)
                issues.append(issue)

        return tuple(sorted(issues, key=_issue_sort_key))


def _issue_sort_key(issue):
    page_id = issue.page_id.value if issue.page_id is not None else ""
    return (
        issue.issue_type.value,
        issue.affected_url.value,
        page_id,
        issue.issue_id.value,
    )
