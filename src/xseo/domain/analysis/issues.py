"""Issue construction helpers."""

from __future__ import annotations

from xseo.domain.analysis.keys import issue_key
from xseo.domain.analysis.policies import DEFAULT_SEVERITY_POLICY
from xseo.domain.entities import Issue
from xseo.domain.ids import IssueId


def build_issue(
    crawl_id,
    page_id,
    affected_url,
    issue_type,
    explanation,
    severity_policy=DEFAULT_SEVERITY_POLICY,
    discriminator="",
    key_subject=None,
):
    key_subject = key_subject or page_id or affected_url
    issue_id = IssueId.create(
        issue_key(crawl_id, issue_type, key_subject, discriminator)
    ).value
    return Issue(
        issue_id=issue_id,
        crawl_id=crawl_id,
        page_id=page_id,
        affected_url=affected_url,
        issue_type=issue_type,
        severity=severity_policy.severity_for(issue_type),
        explanation=explanation,
    )
