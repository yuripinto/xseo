"""Approximate rendered text width, in pixels.

Google truncates titles and meta descriptions in the SERP by **pixel width**,
not character count — a title of 60 narrow characters ("illilli…") fits where 60
wide ones ("WMWMWM…") would be cut. These per-character widths approximate Arial
(the SERP font family) and let the detectors flag titles/descriptions that will
be visually truncated even when they pass the character-count thresholds.

The widths are an estimate, so detection is advisory (LOW severity); the point is
to catch wide-glyph strings that character counts miss.
"""

from __future__ import annotations

_DEFAULT_WIDTH = 8.0

# Rough Arial glyph widths in pixels; average glyph ≈ 8px.
_PIXEL_WIDTHS = {
    " ": 4,
    "!": 4,
    '"': 5,
    "#": 8,
    "$": 8,
    "%": 13,
    "&": 10,
    "'": 3,
    "(": 5,
    ")": 5,
    "*": 6,
    "+": 8,
    ",": 4,
    "-": 5,
    ".": 4,
    "/": 4,
    "0": 8,
    "1": 8,
    "2": 8,
    "3": 8,
    "4": 8,
    "5": 8,
    "6": 8,
    "7": 8,
    "8": 8,
    "9": 8,
    ":": 4,
    ";": 4,
    "<": 8,
    "=": 8,
    ">": 8,
    "?": 7,
    "@": 14,
    "A": 9,
    "B": 9,
    "C": 10,
    "D": 10,
    "E": 9,
    "F": 8,
    "G": 11,
    "H": 10,
    "I": 4,
    "J": 6,
    "K": 9,
    "L": 8,
    "M": 12,
    "N": 10,
    "O": 11,
    "P": 9,
    "Q": 11,
    "R": 10,
    "S": 9,
    "T": 8,
    "U": 10,
    "V": 9,
    "W": 13,
    "X": 9,
    "Y": 9,
    "Z": 8,
    "[": 4,
    "\\": 4,
    "]": 4,
    "^": 7,
    "_": 8,
    "`": 5,
    "a": 8,
    "b": 8,
    "c": 7,
    "d": 8,
    "e": 8,
    "f": 4,
    "g": 8,
    "h": 8,
    "i": 3,
    "j": 3,
    "k": 7,
    "l": 3,
    "m": 12,
    "n": 8,
    "o": 8,
    "p": 8,
    "q": 8,
    "r": 5,
    "s": 7,
    "t": 4,
    "u": 8,
    "v": 7,
    "w": 10,
    "x": 7,
    "y": 7,
    "z": 7,
    "{": 5,
    "|": 4,
    "}": 5,
    "~": 8,
}


def estimate_pixel_width(text: str) -> int:
    """Estimate the rendered width of ``text`` in pixels (Arial approximation)."""
    if not text:
        return 0
    return round(sum(_PIXEL_WIDTHS.get(char, _DEFAULT_WIDTH) for char in text))
