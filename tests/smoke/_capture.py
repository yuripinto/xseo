"""Global error capture for the smoke run.

Installs hooks for:
  * Python's main-thread uncaught exceptions (``sys.excepthook``)
  * Background-thread uncaught exceptions (``threading.excepthook``)
  * Stderr writes (Python ``print`` and C-level via ``sys.stderr``)
  * Qt's log messages (``PySide6.QtCore.qInstallMessageHandler``)

The captured records are reported in a single ``SmokeReport`` so the smoke test
can fail loudly with the actual error text.
"""

from __future__ import annotations

import io
import sys
import threading
import traceback
from dataclasses import dataclass, field

from PySide6.QtCore import QtMsgType, qInstallMessageHandler


@dataclass
class SmokeReport:
    exceptions: list[str] = field(default_factory=list)
    qt_warnings: list[str] = field(default_factory=list)
    qt_criticals: list[str] = field(default_factory=list)
    stderr: io.StringIO = field(default_factory=io.StringIO)

    @property
    def stderr_text(self) -> str:
        return self.stderr.getvalue()

    @property
    def has_failures(self) -> bool:
        return bool(self.exceptions) or bool(self.qt_criticals)

    def summary(self) -> str:
        lines = []
        lines.append(f"exceptions:   {len(self.exceptions)}")
        lines.append(f"qt criticals: {len(self.qt_criticals)}")
        lines.append(f"qt warnings:  {len(self.qt_warnings)}")
        stderr = self.stderr_text.strip()
        lines.append(f"stderr bytes: {len(stderr)}")
        if self.exceptions:
            lines.append("--- exceptions ---")
            lines.extend(self.exceptions)
        if self.qt_criticals:
            lines.append("--- qt criticals ---")
            lines.extend(self.qt_criticals)
        if self.qt_warnings:
            lines.append("--- qt warnings (informational) ---")
            lines.extend(self.qt_warnings)
        if stderr:
            lines.append("--- stderr ---")
            lines.append(stderr)
        return "\n".join(lines)


class _TeeStderr:
    def __init__(self, original, buffer: io.StringIO) -> None:
        self._original = original
        self._buffer = buffer

    def write(self, data: str) -> int:
        self._buffer.write(data)
        return self._original.write(data)

    def flush(self) -> None:
        self._original.flush()

    def __getattr__(self, name: str):
        return getattr(self._original, name)


class CaptureContext:
    """Install all hooks on enter, restore on exit."""

    def __init__(self) -> None:
        self.report = SmokeReport()
        self._original_excepthook = None
        self._original_threading_excepthook = None
        self._original_stderr = None
        self._original_qt_handler = None

    def __enter__(self) -> SmokeReport:
        self._original_excepthook = sys.excepthook
        self._original_threading_excepthook = threading.excepthook
        self._original_stderr = sys.stderr

        sys.excepthook = self._on_main_thread_exception
        threading.excepthook = self._on_thread_exception
        sys.stderr = _TeeStderr(sys.stderr, self.report.stderr)
        self._original_qt_handler = qInstallMessageHandler(self._on_qt_message)
        return self.report

    def __exit__(self, exc_type, exc, tb) -> None:
        qInstallMessageHandler(self._original_qt_handler)
        sys.stderr = self._original_stderr
        threading.excepthook = self._original_threading_excepthook
        sys.excepthook = self._original_excepthook

    def _on_main_thread_exception(self, exc_type, exc, tb) -> None:
        formatted = "".join(traceback.format_exception(exc_type, exc, tb))
        self.report.exceptions.append(f"[main-thread] {formatted}")
        if self._original_excepthook is not None:
            self._original_excepthook(exc_type, exc, tb)

    def _on_thread_exception(self, args) -> None:
        formatted = "".join(
            traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback)
        )
        name = getattr(args.thread, "name", "?")
        self.report.exceptions.append(f"[thread:{name}] {formatted}")
        if self._original_threading_excepthook is not None:
            self._original_threading_excepthook(args)

    def _on_qt_message(self, mode, context, message) -> None:
        text = f"[{context.file}:{context.line}] {message}" if context.file else message
        if mode == QtMsgType.QtCriticalMsg or mode == QtMsgType.QtFatalMsg:
            self.report.qt_criticals.append(text)
        elif mode == QtMsgType.QtWarningMsg:
            self.report.qt_warnings.append(text)
