"""Visible text normalization for extraction."""

from __future__ import annotations

import re

_WHITESPACE = re.compile(r"\s+")


def normalize_visible_text(text):
    if text is None:
        return ""
    return _WHITESPACE.sub(" ", text).strip()


def hash_input_text(text):
    return normalize_visible_text(text).lower()


def word_count(text):
    normalized = normalize_visible_text(text)
    if not normalized:
        return 0
    return len(normalized.split())
