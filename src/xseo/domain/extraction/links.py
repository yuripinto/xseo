"""Raw link extraction from parsed HTML."""

from __future__ import annotations

from xseo.domain.extraction.results import RawExtractedLink


def extract_raw_links(tree, source_url):
    links = []
    for position, node in enumerate(tree.css("a[href]")):
        href = (node.attributes.get("href") or "").strip()
        if not href or href.startswith("#"):
            continue
        rel = node.attributes.get("rel")
        rel_value = rel.strip() if isinstance(rel, str) else None
        links.append(
            RawExtractedLink(
                raw_href=href,
                source_url=source_url,
                anchor_text=(node.text() or "").strip(),
                rel=rel_value,
                nofollow="nofollow" in (rel_value or "").lower().split(),
                position=position,
            )
        )
    return tuple(links)
