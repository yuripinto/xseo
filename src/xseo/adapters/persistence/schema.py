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
    content_hash TEXT,
    image_count INTEGER NOT NULL DEFAULT 0,
    images_missing_alt INTEGER NOT NULL DEFAULT 0,
    has_viewport INTEGER NOT NULL DEFAULT 0,
    has_lang INTEGER NOT NULL DEFAULT 0,
    has_charset INTEGER NOT NULL DEFAULT 0,
    has_open_graph INTEGER NOT NULL DEFAULT 0,
    has_structured_data INTEGER NOT NULL DEFAULT 0,
    mixed_content_count INTEGER NOT NULL DEFAULT 0,
    has_hreflang INTEGER NOT NULL DEFAULT 0,
    hreflang_self_referential INTEGER NOT NULL DEFAULT 1,
    depth INTEGER NOT NULL DEFAULT 0,
    images_missing_dimensions INTEGER NOT NULL DEFAULT 0,
    structured_data_invalid INTEGER NOT NULL DEFAULT 0
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


# Additive column migrations for databases created before these columns existed.
# The CREATE TABLE above covers fresh databases; these ALTERs backfill existing
# ones. Each entry is (column_name, ddl_statement) and is applied only when the
# column is absent, so running them repeatedly is safe.
PAGE_COLUMN_MIGRATIONS = (
    (
        "image_count",
        "ALTER TABLE pages ADD COLUMN image_count INTEGER NOT NULL DEFAULT 0",
    ),
    (
        "images_missing_alt",
        "ALTER TABLE pages ADD COLUMN images_missing_alt INTEGER NOT NULL DEFAULT 0",
    ),
    (
        "has_viewport",
        "ALTER TABLE pages ADD COLUMN has_viewport INTEGER NOT NULL DEFAULT 0",
    ),
    (
        "has_lang",
        "ALTER TABLE pages ADD COLUMN has_lang INTEGER NOT NULL DEFAULT 0",
    ),
    (
        "has_charset",
        "ALTER TABLE pages ADD COLUMN has_charset INTEGER NOT NULL DEFAULT 0",
    ),
    (
        "has_open_graph",
        "ALTER TABLE pages ADD COLUMN has_open_graph INTEGER NOT NULL DEFAULT 0",
    ),
    (
        "has_structured_data",
        "ALTER TABLE pages ADD COLUMN has_structured_data INTEGER NOT NULL DEFAULT 0",
    ),
    (
        "mixed_content_count",
        "ALTER TABLE pages ADD COLUMN mixed_content_count INTEGER NOT NULL DEFAULT 0",
    ),
    (
        "has_hreflang",
        "ALTER TABLE pages ADD COLUMN has_hreflang INTEGER NOT NULL DEFAULT 0",
    ),
    (
        "hreflang_self_referential",
        "ALTER TABLE pages ADD COLUMN hreflang_self_referential INTEGER NOT NULL DEFAULT 1",
    ),
    (
        "depth",
        "ALTER TABLE pages ADD COLUMN depth INTEGER NOT NULL DEFAULT 0",
    ),
    (
        "images_missing_dimensions",
        "ALTER TABLE pages ADD COLUMN images_missing_dimensions INTEGER NOT NULL DEFAULT 0",
    ),
    (
        "structured_data_invalid",
        "ALTER TABLE pages ADD COLUMN structured_data_invalid INTEGER NOT NULL DEFAULT 0",
    ),
)
