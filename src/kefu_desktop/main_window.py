from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QTimer, QUrl, Signal, Slot
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QHBoxLayout,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QWidget,
)

from .backend_manager import BackendManager
from .pages.ai_settings import AISettingsPage
from .pages.dashboard import DashboardPage
from .pages.logs import LogsPage
from .pages.platforms import PlatformsPage


class _LogBridge(QObject):
    line = Signal(str, str)


class MainWindow(QMainWindow):
    def __init__(
        self, project_root: str | Path | None = None, config: object | None = None
    ) -> None:
        super().__init__()
        self.setWindowTitle("AI 电商客服")
        self.resize(980, 680)
        self.project_root = Path(project_root or Path(__file__).resolve().parents[2]).resolve()
        self.config = config
        self._bridge = _LogBridge()
        backend_env = {}
        build_env = getattr(self.config, "build_backend_env", None)
        if callable(build_env):
            backend_env = build_env()
        self.backend = BackendManager(
            self.project_root,
            env=backend_env,
            log_callback=lambda stream, line: self._bridge.line.emit(stream, line),
        )
        self.dashboard = DashboardPage()
        self.ai_settings = AISettingsPage(config)
        self.platforms = PlatformsPage()
        self.logs = LogsPage()
        self._pages = QStackedWidget()
        [
            self._pages.addWidget(page)
            for page in (self.dashboard, self.ai_settings, self.platforms, self.logs)
        ]
        nav = QListWidget()
        nav.addItems(["首页 / 控制台", "AI 设置", "平台管理", "运行日志"])
        nav.setFixedWidth(160)
        nav.currentRowChanged.connect(self._pages.setCurrentIndex)
        nav.setCurrentRow(0)
        body = QWidget()
        layout = QHBoxLayout(body)
        layout.addWidget(nav)
        layout.addWidget(self._pages, 1)
        self.setCentralWidget(body)
        self.dashboard.start_requested.connect(self.start_backend)
        self.dashboard.stop_requested.connect(self.stop_backend)
        self.dashboard.logs_requested.connect(self.open_log_directory)
        self._bridge.line.connect(self.logs.append_log)
        self.ai_settings.settings_saved.connect(self._settings_saved)
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.refresh_status)
        self._timer.start(1500)
        self.refresh_status()

    @Slot()
    def start_backend(self) -> None:
        if not self.backend.start() and self.backend.last_error:
            QMessageBox.critical(self, "启动失败", self.backend.last_error)
        self.refresh_status()

    @Slot()
    def stop_backend(self) -> None:
        self.backend.stop()
        self.refresh_status()

    @Slot()
    def refresh_status(self) -> None:
        status = self.backend.status()
        self.dashboard.set_state(
            status, status == "running" and self.backend.health(), self._provider()
        )

    def _provider(self) -> str:
        values = getattr(self.config, "get_provider_settings", lambda: {})() if self.config else {}
        provider = (values or {}).get("provider")
        if not provider and self.config:
            loader = getattr(self.config, "load", None)
            env_values = loader() if callable(loader) else {}
            provider = (env_values or {}).get("CLAWBOT_DECISION_MODE")
        return str(provider or "deepseek")

    def _settings_saved(self, values: dict) -> None:
        build_env = getattr(self.config, "build_backend_env", None)
        if callable(build_env):
            self.backend.update_environment(build_env())
        self.dashboard.model_label.setText(
            "OpenClaw" if values.get("provider") == "openclaw" else "DeepSeek"
        )

    def open_log_directory(self) -> None:
        path = self.project_root / "logs"
        path.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def closeEvent(self, event) -> None:  # noqa: N802
        self.backend.close()
        event.accept()
