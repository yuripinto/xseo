"""Read-side application service."""

from __future__ import annotations

from xseo.application.query import validate_query_options
from xseo.application.results import ApplicationResult


class ResultsApplicationService:
    def __init__(self, read_repository):
        self.read_repository = read_repository

    def list_pages(self, query):
        validation = validate_query_options(query.options, {"url", "final_url", "status_code", "title", "word_count", "content_type"})
        if not validation.success:
            return validation
        return ApplicationResult.ok(tuple(self.read_repository.list_pages(query)))

    def list_issues(self, query):
        validation = validate_query_options(query.options, {"affected_url", "issue_type", "severity", "explanation"})
        if not validation.success:
            return validation
        return ApplicationResult.ok(tuple(self.read_repository.list_issues(query)))

    def list_duplicate_groups(self, query):
        validation = validate_query_options(query.options, {"content_hash", "page_count", "representative_url"})
        if not validation.success:
            return validation
        return ApplicationResult.ok(tuple(self.read_repository.list_duplicate_groups(query)))

    def get_page_detail(self, query):
        detail = self.read_repository.get_page_detail(query)
        if detail is None:
            return ApplicationResult.fail("Page detail was not found", "page_detail.not_found")
        return ApplicationResult.ok(detail)

    def get_recent_crawl(self):
        crawl = self.read_repository.find_recent_crawl()
        if crawl is None:
            return ApplicationResult.fail("No recent crawl was found", "crawl.no_recent")
        return ApplicationResult.ok(crawl)
