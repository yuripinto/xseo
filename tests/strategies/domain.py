from datetime import UTC, datetime

from hypothesis import strategies as st

from xseo.domain.entities import Crawl, CrawlConfig, ExtractedPage
from xseo.domain.enums import CrawlStatus, IssueSeverity, IssueType
from xseo.domain.events import CrawlStarted
from xseo.domain.ids import CrawlId, PageId
from xseo.domain.urls import BaseUrl, NormalizedUrl, RawUrl
from xseo.domain.value_objects import ContentHash, WordCount


non_empty_text = st.text(min_size=1).filter(lambda value: bool(value.strip()))
http_hosts = st.from_regex(r"[a-z]{1,12}\.example\.com", fullmatch=True)
http_urls = st.builds(lambda host: f"https://{host}/", http_hosts)
invalid_urls = st.one_of(st.just(""), st.just("ftp://example.com"), st.just("https:///missing"))


def valid_url_strings(host=None):
    host_strategy = st.just(host) if host else st.just("example.com")
    path = st.lists(
        st.text(
            alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd")),
            min_size=1,
            max_size=8,
        ),
        min_size=0,
        max_size=3,
    ).map(lambda parts: "/" + "/".join(parts) if parts else "/")
    query = st.one_of(
        st.just(""),
        st.integers(min_value=0, max_value=100).map(lambda value: f"?q={value}"),
    )
    fragment = st.one_of(st.just(""), st.just("#section"))
    return st.builds(lambda host_value, path_value, query_value, frag: f"https://{host_value}{path_value}{query_value}{frag}", host_strategy, path, query, fragment)


def same_host_url_sequences():
    return st.lists(valid_url_strings("example.com"), min_size=1, max_size=30)


def html_documents_with_links():
    hrefs = st.lists(
        st.one_of(
            st.just(""),
            st.just("#section"),
            st.just("/relative"),
            st.just("https://example.com/page"),
            st.just("https://other.example.com/page"),
        ),
        min_size=0,
        max_size=10,
    )
    return hrefs.map(
        lambda values: "<html><body>"
        + "".join(f'<a href="{href}">link</a>' for href in values)
        + "</body></html>"
    )


def malformed_html_fragments():
    return st.one_of(
        st.just("<html><title>Broken<body><h1>Missing close"),
        st.just("<div><span>nested"),
        st.text(max_size=200),
    )


def visible_text_variants():
    base = st.text(
        alphabet="abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789",
        min_size=1,
        max_size=30,
    ).filter(lambda value: bool(value.strip()))
    return base.map(lambda value: (value, f"  {value.upper()}  "))


@st.composite
def crawl_ids(draw):
    return CrawlId.create(draw(non_empty_text)).value


@st.composite
def page_ids(draw):
    return PageId.create(draw(non_empty_text)).value


@st.composite
def raw_urls(draw):
    return RawUrl.create(draw(st.one_of(http_urls, st.just("/relative")))).value


@st.composite
def base_urls(draw):
    return BaseUrl.create(draw(http_urls)).value


@st.composite
def normalized_urls(draw):
    return NormalizedUrl.create(draw(http_urls)).value


@st.composite
def crawl_configs(draw):
    return CrawlConfig.create(
        draw(base_urls()),
        same_host_only=draw(st.booleans()),
        page_limit=draw(st.integers(min_value=1, max_value=1000)),
        timeout_seconds=draw(st.integers(min_value=1, max_value=60)),
    ).value


@st.composite
def crawls(draw):
    return Crawl.create(
        draw(crawl_ids()),
        draw(crawl_configs()),
        datetime(2026, 1, 1, tzinfo=UTC),
    )


crawl_statuses = st.sampled_from(list(CrawlStatus))
issue_severities = st.sampled_from(list(IssueSeverity))
issue_types = st.sampled_from(list(IssueType))
seo_text = st.text(
    alphabet=st.characters(whitelist_categories=("Ll", "Lu", "Nd", "Zs")),
    min_size=0,
    max_size=220,
)
content_hash_values = st.text(
    alphabet="abcdef0123456789",
    min_size=8,
    max_size=32,
).filter(lambda value: bool(value.strip()))


@st.composite
def crawl_started_events(draw):
    return CrawlStarted(
        crawl_id=draw(crawl_ids()),
        occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
        config=draw(crawl_configs()),
    )


@st.composite
def content_hashes(draw):
    return ContentHash.create(draw(content_hash_values)).value


@st.composite
def word_counts(draw, min_value=0, max_value=1000):
    return WordCount.create(draw(st.integers(min_value=min_value, max_value=max_value))).value


@st.composite
def extracted_pages(draw, crawl_id=None, page_id=None, content_hash=None):
    selected_crawl_id = crawl_id or draw(crawl_ids())
    selected_page_id = page_id or draw(page_ids())
    url = draw(normalized_urls())
    selected_hash = content_hash
    if selected_hash is None:
        selected_hash = draw(st.one_of(content_hashes(), st.none()))
    return ExtractedPage(
        page_id=selected_page_id,
        crawl_id=selected_crawl_id,
        url=url,
        final_url=url,
        status_code=200,
        content_type="text/html",
        title=draw(st.one_of(seo_text, st.none())),
        meta_description=draw(st.one_of(seo_text, st.none())),
        canonical_url=draw(st.one_of(st.just(url), st.none())),
        robots_meta=None,
        word_count=draw(word_counts()),
        content_length=draw(st.integers(min_value=0, max_value=100000)),
        content_hash=selected_hash,
    )


# UOW-005 application strategy helpers
from xseo.application.commands import QueryOptions
from xseo.application.events import CrawlProgressEvent, CrawlProgressEventKind
from xseo.application.read_models import PageRow


@st.composite
def crawl_progress_events(draw, crawl_id=None):
    selected_crawl_id = crawl_id or draw(crawl_ids())
    return CrawlProgressEvent(
        crawl_id=selected_crawl_id,
        kind=draw(st.sampled_from(list(CrawlProgressEventKind))),
        status=draw(crawl_statuses),
        occurred_at=datetime(2026, 1, 1, tzinfo=UTC),
        message=draw(st.one_of(st.none(), seo_text)),
    )


subscription_actions = st.lists(
    st.sampled_from(("subscribe", "unsubscribe", "publish")),
    min_size=1,
    max_size=20,
)

stop_request_counts = st.integers(min_value=1, max_value=20)


@st.composite
def page_rows(draw):
    url = draw(normalized_urls())
    return PageRow(
        page_id=draw(page_ids()),
        url=url,
        final_url=url,
        status_code=draw(st.sampled_from((200, 301, 404, 500))),
        title=draw(st.one_of(seo_text, st.none())),
        meta_description=draw(st.one_of(seo_text, st.none())),
        canonical_url=draw(st.one_of(st.just(url), st.none())),
        word_count=draw(st.integers(min_value=0, max_value=2000)),
        content_type="text/html",
    )


query_options = st.builds(
    QueryOptions,
    filters=st.just(None),
    sort_field=st.one_of(st.none(), st.sampled_from(("url", "status_code", "title", "word_count"))),
    sort_direction=st.sampled_from(("asc", "desc")),
    page_size=st.one_of(st.none(), st.integers(min_value=1, max_value=25)),
    offset=st.integers(min_value=0, max_value=10),
)
