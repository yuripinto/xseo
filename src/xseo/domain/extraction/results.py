"""Support objects for SEO extraction boundaries."""

from __future__ import annotations

from dataclasses import dataclass

from xseo.domain.entities import ExtractionResult
from xseo.domain.urls import NormalizedUrl


@dataclass(frozen=True)
class RawExtractedLink:
    raw_href: str
    source_url: NormalizedUrl
    anchor_text: str = ""
    rel: str | None = None
    nofollow: bool = False
    position: int = 0


@dataclass(frozen=True)
class SeoExtractionOutput:
    extraction_result: ExtractionResult
    raw_links: tuple[RawExtractedLink, ...] = ()
