from __future__ import annotations

from datetime import datetime

from PySide6.QtWidgets import QPlainTextEdit, QVBoxLayout, QWidget


class LogsPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        layout = QVBoxLayout(self)
        layout.addWidget(self.output)

    def append_log(self, stream: str, line: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        self.output.appendPlainText(f"[{stamp}] [{stream}] {line}")
