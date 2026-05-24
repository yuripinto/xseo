"""Stop-token collaborators for crawl execution."""

from __future__ import annotations

from typing import Protocol


class StopToken(Protocol):
    def is_stop_requested(self): ...


class NeverStopToken:
    def is_stop_requested(self):
        return False
