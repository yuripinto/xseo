"""Deterministic keys for analysis outputs."""

from __future__ import annotations

import re


_WHITESPACE = re.compile(r"\s+")


def normalize_comparable_text(value):
    if value is None:
        return ""
    return _WHITESPACE.sub(" ", value.strip()).casefold()


def issue_key(crawl_id, issue_type, page_or_url, discriminator=""):
    parts = [
        crawl_id.value,
        issue_type.value,
        getattr(page_or_url, "value", str(page_or_url)),
        discriminator,
    ]
    return "|".join(parts)


def duplicate_group_key(crawl_id, content_hash):
    return f"{crawl_id.value}|exact_duplicate|{content_hash.value}"
