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


def detect_insecure_link_issues(pages, links, severity_policy=DEFAULT_SEVERITY_POLICY):
    secure_pages = {
        page.page_id.value: page for page in pages if _is_https(page.final_url)
    }
    issues = []
    for link in links:
        if link.relation != LinkRelation.INTERNAL:
            continue
        source = secure_pages.get(link.source_page_id.value)
        if source is None or not _is_http(link.target_url):
            continue
        issues.append(
            build_issue(
                source.crawl_id,
                source.page_id,
                source.final_url,
                IssueType.INSECURE_INTERNAL_LINK,
                f"Secure page links to an insecure (http) URL: {link.target_url.value}",
                severity_policy,
                discriminator=link.target_url.value,
                key_subject=source.page_id,
            )
        )
    return tuple(issues)


def _is_https(url):
    return url.value.lower().startswith("https://")


def _is_http(url):
    return url.value.lower().startswith("http://")
