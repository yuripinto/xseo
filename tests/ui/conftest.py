"""Configure headless Qt for CI and local test runs."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
