"""SQLite schema for xseo persistence."""

SCHEMA_VERSION = 1

DDL = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY
);

INSERT OR IGNORE INTO schema_version(version) VALUES (1);

CREATE TABLE IF NOT EXISTS crawls (
    crawl_id TEXT PRIMARY KEY,
    start_url TEXT NOT NULL,
    same_host_only INTEGER NOT NULL,
    page_limit INTEGER NOT NULL,
    timeout_seconds INTEGER NOT NULL,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    started_at TEXT,
    completed_at TEXT,
    failure_code TEXT,
    failure_message TEXT
);

CREATE TABLE IF NOT EXISTS pages (
    page_id TEXT PRIMARY KEY,
    crawl_id TEXT NOT NULL REFERENCES crawls(crawl_id) ON DELETE CASCADE,
    url TEXT NOT NULL,
    final_url TEXT NOT NULL,
    status_code INTEGER NOT NULL,
    content_type TEXT,
    title TEXT,
    meta_description TEXT,
    canonical_url TEXT,
    robots_meta TEXT,
    word_count INTEGER NOT NULL,
    content_length INTEGER NOT NULL,
    content_hash TEXT
);

CREATE TABLE IF NOT EXISTS links (
    source_page_id TEXT NOT NULL REFERENCES pages(page_id) ON DELETE CASCADE,
    target_url TEXT NOT NULL,
    relation TEXT NOT NULL,
    anchor_text TEXT NOT NULL,
    nofollow INTEGER NOT NULL,
    PRIMARY KEY (source_page_id, target_url, anchor_text, relation)
);

CREATE TABLE IF NOT EXISTS headings (
    page_id TEXT NOT NULL REFERENCES pages(page_id) ON DELETE CASCADE,
    level TEXT NOT NULL,
    text TEXT NOT NULL,
    position INTEGER NOT NULL,
    PRIMARY KEY (page_id, level, position, text)
);

CREATE TABLE IF NOT EXISTS redirects (
    crawl_id TEXT NOT NULL REFERENCES crawls(crawl_id) ON DELETE CASCADE,
    from_url TEXT NOT NULL,
    to_url TEXT NOT NULL,
    status_code INTEGER NOT NULL,
    PRIMARY KEY (crawl_id, from_url, to_url, status_code)
);

CREATE TABLE IF NOT EXISTS issues (
    issue_id TEXT PRIMARY KEY,
    crawl_id TEXT NOT NULL REFERENCES crawls(crawl_id) ON DELETE CASCADE,
    page_id TEXT REFERENCES pages(page_id) ON DELETE SET NULL,
    affected_url TEXT NOT NULL,
    issue_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    explanation TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS duplicate_groups (
    duplicate_group_id TEXT PRIMARY KEY,
    crawl_id TEXT NOT NULL REFERENCES crawls(crawl_id) ON DELETE CASCADE,
    content_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS duplicate_group_pages (
    duplicate_group_id TEXT NOT NULL REFERENCES duplicate_groups(duplicate_group_id) ON DELETE CASCADE,
    page_id TEXT NOT NULL REFERENCES pages(page_id) ON DELETE CASCADE,
    PRIMARY KEY (duplicate_group_id, page_id)
);

CREATE TABLE IF NOT EXISTS exports (
    export_id TEXT PRIMARY KEY,
    crawl_id TEXT NOT NULL REFERENCES crawls(crawl_id) ON DELETE CASCADE,
    kind TEXT NOT NULL,
    target_path TEXT NOT NULL,
    row_count INTEGER NOT NULL,
    success INTEGER NOT NULL,
    error_code TEXT,
    error_message TEXT
);

CREATE INDEX IF NOT EXISTS idx_pages_crawl ON pages(crawl_id);
CREATE INDEX IF NOT EXISTS idx_pages_status ON pages(crawl_id, status_code, page_id);
CREATE INDEX IF NOT EXISTS idx_issues_crawl ON issues(crawl_id);
CREATE INDEX IF NOT EXISTS idx_issues_type ON issues(crawl_id, issue_type, issue_id);
CREATE INDEX IF NOT EXISTS idx_issues_severity ON issues(crawl_id, severity, issue_id);
CREATE INDEX IF NOT EXISTS idx_duplicate_groups_crawl ON duplicate_groups(crawl_id, content_hash);
CREATE INDEX IF NOT EXISTS idx_duplicate_group_pages_page ON duplicate_group_pages(page_id);
"""
