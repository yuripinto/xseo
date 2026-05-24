"""Stable content hashing for extracted visible text."""

from __future__ import annotations

from hashlib import sha256

from xseo.domain.extraction.text import hash_input_text
from xseo.domain.value_objects import ContentHash


def content_hash_for_text(text):
    digest = sha256(hash_input_text(text).encode("utf-8")).hexdigest()
    return ContentHash.create(digest).value
