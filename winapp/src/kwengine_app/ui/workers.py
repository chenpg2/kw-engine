"""QThread worker for pipeline runs — keeps the UI responsive, streams log lines."""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal


class Worker(QThread):
    log_line = Signal(str, str)      # level, text
    done = Signal(object)            # result
    failed = Signal(str)             # error message

    def __init__(self, fn, parent=None):
        """fn: callable(log) -> result, where log(level, text) is thread-safe."""
        super().__init__(parent)
        self._fn = fn

    def run(self) -> None:
        try:
            result = self._fn(lambda level, text: self.log_line.emit(level, text))
            self.done.emit(result)
        except Exception as e:  # surfaced to the user — no silent fallback
            self.failed.emit(str(e))
