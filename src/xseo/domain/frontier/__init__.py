"""URL normalization and frontier behavior."""

from xseo.domain.frontier.frontier import UrlFrontier
from xseo.domain.frontier.normalization import UrlNormalizer
from xseo.domain.frontier.results import (
    FrontierAddResult,
    FrontierAddStatus,
    FrontierAddSummary,
    FrontierEntry,
    FrontierEntryState,
    FrontierSnapshot,
    RejectedUrl,
    RejectionReason,
)

__all__ = [
    "FrontierAddResult",
    "FrontierAddStatus",
    "FrontierAddSummary",
    "FrontierEntry",
    "FrontierEntryState",
    "FrontierSnapshot",
    "RejectedUrl",
    "RejectionReason",
    "UrlFrontier",
    "UrlNormalizer",
]
