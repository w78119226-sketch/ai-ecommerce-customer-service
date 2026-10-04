"""Launch the AI Commerce Customer Service desktop client."""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from .main_window import MainWindow


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    config = None
    try:
        from .config import ConfigStore

        config = ConfigStore(root)
    except (ImportError, OSError, TypeError):
        config = None
    app = QApplication(sys.argv)
    window = MainWindow(root, config)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
