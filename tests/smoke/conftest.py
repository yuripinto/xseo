"""Headless Qt for the smoke suite."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
