"""Thread-safe bridge from background crawl events to the Qt main thread."""

from __future__ import annotations

import queue

from PySide6.QtCore import QObject, QTimer, Signal


class EventBridge(QObject):
    """Receives events from any thread; emits progress signal on the Qt main thread."""

    progress: Signal = Signal(object)

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._queue: queue.Queue[object] = queue.Queue()
        self._timer = QTimer(self)
        self._timer.setInterval(250)
        self._timer.timeout.connect(self._drain)
        self._timer.start()

    def enqueue(self, event: object) -> None:
        """Call from any thread."""
        self._queue.put_nowait(event)

    def _drain(self) -> None:
        while True:
            try:
                event = self._queue.get_nowait()
            except queue.Empty:
                break
            self.progress.emit(event)
