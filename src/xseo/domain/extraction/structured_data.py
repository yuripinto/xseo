"""JSON-LD structured-data validation.

``has_structured_data`` only tells us a ``<script type="application/ld+json">``
block exists. This module inspects the block contents so the analysis layer can
flag structured data that is present but broken — the kind search engines silently
ignore: malformed JSON, or objects missing the ``@context`` / ``@type`` that make
JSON-LD meaningful.

Pure functions; the pipeline passes the raw block strings it pulled from the tree.
"""

from __future__ import annotations

import json
from collections.abc import Iterable


def has_invalid_structured_data(blocks: Iterable[str]) -> bool:
    """True if any JSON-LD block is malformed or missing @context/@type."""
    return any(_block_is_invalid(block) for block in blocks)


def _block_is_invalid(raw: str) -> bool:
    text = (raw or "").strip()
    if not text:
        return True
    try:
        data = json.loads(text)
    except ValueError:
        return True

    nodes = _dict_nodes(data)
    if not nodes:
        return True
    has_type = any("@type" in node for node in nodes)
    has_context = any("@context" in node for node in nodes)
    return not (has_type and has_context)


def _dict_nodes(data) -> list[dict]:
    """Flatten a parsed JSON-LD document into every object (dict) it contains."""
    nodes: list[dict] = []
    if isinstance(data, dict):
        nodes.append(data)
        for value in data.values():
            nodes.extend(_dict_nodes(value))
    elif isinstance(data, list):
        for item in data:
            nodes.extend(_dict_nodes(item))
    return nodes
