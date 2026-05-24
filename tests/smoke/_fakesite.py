"""Tiny in-process HTTP server that serves a small linked SEO test site.

Designed for the smoke test: gives the crawler something deterministic to walk
without touching the network.
"""

from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# Each page links to the others so the crawler's link discovery actually
# traverses the site. Includes intentional SEO defects so the analysis stage
# produces issues and duplicates.
PAGES: dict[str, tuple[str, bytes]] = {
    "/": (
        "text/html; charset=utf-8",
        b"""<!doctype html>
<html><head>
<title>Fixture Home</title>
<meta name="description" content="Smoke fixture home page">
<link rel="canonical" href="http://HOST/">
</head><body>
<h1>Home</h1>
<p>Shared visible body for duplicate detection here.</p>
<a href="/about">About</a>
<a href="/duplicate">Duplicate</a>
<a href="/missing-title">Missing title</a>
</body></html>""",
    ),
    "/about": (
        "text/html; charset=utf-8",
        b"""<!doctype html>
<html><head>
<title>About</title>
<meta name="description" content="About this smoke fixture">
</head><body>
<h1>About</h1>
<p>An about page with its own unique body content for testing.</p>
<a href="/">Home</a>
</body></html>""",
    ),
    "/duplicate": (
        "text/html; charset=utf-8",
        b"""<!doctype html>
<html><head>
<title>Fixture Home</title>
<meta name="description" content="Smoke fixture home page">
</head><body>
<h1>Home</h1>
<p>Shared visible body for duplicate detection here.</p>
<a href="/about">About</a>
<a href="/duplicate">Duplicate</a>
<a href="/missing-title">Missing title</a>
</body></html>""",
    ),
    "/missing-title": (
        "text/html; charset=utf-8",
        b"""<!doctype html>
<html><head>
<meta name="description" content="No title on purpose for issue detection">
</head><body>
<h1>Missing title</h1>
<p>This page has no title element so the analyzer must flag it.</p>
<a href="/">Home</a>
</body></html>""",
    ),
}


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:  # noqa: N802
        path = self.path.split("?", 1)[0].rstrip("/") or "/"
        entry = PAGES.get(path)
        if entry is None:
            self.send_response(404)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"not found")
            return
        ctype, body = entry
        host = self.headers.get("Host", f"127.0.0.1:{self.server.server_port}")
        body = body.replace(b"HOST", host.encode())
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:  # noqa: A002, D401
        return


class FakeSite:
    """Start/stop wrapper for a localhost test site."""

    def __init__(self) -> None:
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self._thread = threading.Thread(
            target=self._server.serve_forever, daemon=True
        )

    @property
    def port(self) -> int:
        return self._server.server_address[1]

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}/"

    def start(self) -> "FakeSite":
        self._thread.start()
        return self

    def stop(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=2)
