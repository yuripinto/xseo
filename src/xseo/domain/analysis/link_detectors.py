"""Internal link status issue detectors."""

from __future__ import annotations

from dataclasses import dataclass

from xseo.domain.analysis.issues import build_issue
from xseo.domain.analysis.policies import DEFAULT_SEVERITY_POLICY
from xseo.domain.enums import IssueType, LinkRelation


@dataclass(frozen=True)
class LinkStatusRecord:
    source_page_id: object
    source_url: object
    target_url: object
    relation: LinkRelation
    status_code: int | None
    final_url: object | None = None


def detect_link_issues(crawl_id, records, severity_policy=DEFAULT_SEVERITY_POLICY):
    issues = []
    for record in records:
        if record.relation != LinkRelation.INTERNAL or record.status_code is None:
            continue
        if 400 <= record.status_code <= 599:
            issues.append(
                build_issue(
                    crawl_id,
                    record.source_page_id,
                    record.target_url,
                    IssueType.BROKEN_INTERNAL_LINK,
                    f"Internal link returned HTTP {record.status_code}.",
                    severity_policy,
                    discriminator=str(record.status_code),
                    key_subject=record.target_url,
                )
            )
        elif 300 <= record.status_code <= 399:
            issues.append(
                build_issue(
                    crawl_id,
                    record.source_page_id,
                    record.target_url,
                    IssueType.REDIRECTING_URL,
                    f"Internal link returned redirect HTTP {record.status_code}.",
                    severity_policy,
                    discriminator=str(record.status_code),
                    key_subject=record.target_url,
                )
            )
    return tuple(issues)
