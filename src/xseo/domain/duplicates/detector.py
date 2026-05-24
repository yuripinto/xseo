"""Exact duplicate content detection."""

from __future__ import annotations

from collections import defaultdict

from xseo.domain.analysis.keys import duplicate_group_key
from xseo.domain.entities import DuplicateGroup
from xseo.domain.ids import DuplicateGroupId


def detect_duplicate_groups(crawl_id, pages):
    groups = defaultdict(list)
    hashes = {}
    for page in pages:
        if page.content_hash is None or not page.content_hash.value.strip():
            continue
        groups[page.content_hash.value].append(page.page_id)
        hashes[page.content_hash.value] = page.content_hash

    duplicates = []
    for hash_value in sorted(groups):
        page_ids = tuple(sorted(groups[hash_value], key=lambda page_id: page_id.value))
        if len(page_ids) < 2:
            continue
        content_hash = hashes[hash_value]
        group_id = DuplicateGroupId.create(
            duplicate_group_key(crawl_id, content_hash)
        ).value
        duplicates.append(
            DuplicateGroup.create(group_id, crawl_id, content_hash, page_ids).value
        )
    return tuple(duplicates)
