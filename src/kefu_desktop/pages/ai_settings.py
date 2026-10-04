from __future__ import annotations

import json
import urllib.error
import urllib.request

from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class _ConnectionWorker(QObject):
    finished = Signal(bool, str)

    def __init__(self, api_key: str, base_url: str, model: str, timeout: int) -> None:
        super().__init__()
        self.api_key, self.base_url, self.model, self.timeout = api_key, base_url, model, timeout

    @Slot()
    def run(self) -> None:
        if not self.api_key.strip():
            self.finished.emit(False, "API Key 错误")
            return
        payload = {
            "model": self.model.strip(),
            "messages": [{"role": "user", "content": "你好"}],
            "max_tokens": 8,
        }
        request = urllib.request.Request(
            self.base_url.rstrip("/") + "/chat/completions",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            method="POST",
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(request, timeout=max(1, self.timeout)) as response:
                if not 200 <= int(response.status) < 300:
                    raise urllib.error.HTTPError(
                        request.full_url, int(response.status), "", response.headers, None
                    )
                result = json.loads(response.read().decode("utf-8"))
                if (
                    not isinstance(result, dict)
                    or not isinstance(result.get("choices"), list)
                    or not result["choices"]
                ):
                    self.finished.emit(False, "API 返回异常")
                    return
        except TimeoutError:
            self.finished.emit(False, "请求超时")
        except urllib.error.HTTPError as exc:
            self.finished.emit(
                False,
                "API Key 错误" if exc.code in (401, 403) else f"API 返回异常（HTTP {exc.code}）",
            )
        except urllib.error.URLError as exc:
            self.finished.emit(
                False, "请求超时" if isinstance(exc.reason, TimeoutError) else "网络连接失败"
            )
        except (ConnectionError, OSError):
            self.finished.emit(False, "网络连接失败")
        except ValueError:
            self.finished.emit(False, "API 返回异常")
        else:
            self.finished.emit(True, "连接成功")


class AISettingsPage(QWidget):
    settings_saved = Signal(dict)

    def __init__(self, config: object | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.config = config
        self.provider = QComboBox()
        self.provider.addItems(["DeepSeek", "OpenClaw"])
        self.api_key = QLineEdit()
        self.api_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.base_url = QLineEdit("https://api.deepseek.com")
        self.model = QLineEdit("deepseek-chat")
        self.timeout = QSpinBox()
        self.timeout.setRange(1, 600)
        self.timeout.setValue(60)
        form = QFormLayout()
        form.addRow("模型提供商", self.provider)
        form.addRow("API Key", self.api_key)
        form.addRow("Base URL", self.base_url)
        form.addRow("Model", self.model)
        form.addRow("Timeout", self.timeout)
        box = QGroupBox("模型配置")
        box.setLayout(form)
        save = QPushButton("保存设置")
        test = QPushButton("测试连接")
        self.status = QLabel()
        save.clicked.connect(self.save)
        test.clicked.connect(self.test_connection)
        actions = QVBoxLayout()
        actions.addWidget(save)
        actions.addWidget(test)
        actions.addWidget(self.status)
        layout = QVBoxLayout(self)
        layout.addWidget(box)
        layout.addLayout(actions)
        layout.addStretch(1)
        self.load()

    def load(self) -> None:
        getter = getattr(self.config, "get_provider_settings", None)
        values = getter() if callable(getter) else {}
        values = values or {}
        raw_mode = values.get("provider", values.get("decision_mode"))
        if not raw_mode:
            loader = getattr(self.config, "load", None)
            env_values = loader() if callable(loader) else {}
            raw_mode = (env_values or {}).get("CLAWBOT_DECISION_MODE", "deepseek")
        provider = str(raw_mode).lower()
        self.provider.setCurrentIndex(1 if provider in {"openclaw", "agent"} else 0)
        self.api_key.setText(str(values.get("api_key", "")))
        self.base_url.setText(str(values.get("base_url") or "https://api.deepseek.com"))
        self.model.setText(str(values.get("model") or "deepseek-chat"))
        try:
            self.timeout.setValue(int(values.get("timeout") or 60))
        except (TypeError, ValueError):
            pass

    def values(self) -> dict:
        return {
            "provider": "openclaw" if self.provider.currentIndex() else "deepseek",
            "api_key": self.api_key.text(),
            "base_url": self.base_url.text().strip(),
            "model": self.model.text().strip(),
            "timeout": self.timeout.value(),
        }

    @Slot()
    def save(self) -> None:
        values = self.values()
        saver = getattr(self.config, "save_provider_settings", None)
        if callable(saver):
            saver(**values)
        env_path = getattr(self.config, "env_path", None)
        if env_path is not None:
            try:
                from ..config import update_env

                update_env(env_path, {"CLAWBOT_DECISION_MODE": values["provider"]})
            except (ImportError, OSError):
                pass
        self.settings_saved.emit(values)
        self.status.setText("设置已保存")

    @Slot()
    def test_connection(self) -> None:
        if self.provider.currentIndex() == 1:
            self.status.setText("OpenClaw 不需要 DeepSeek 连接测试")
            return
        from PySide6.QtCore import QThread

        self.status.setText("正在测试连接…")
        self._thread = QThread(self)
        self._worker = _ConnectionWorker(
            self.api_key.text(), self.base_url.text(), self.model.text(), self.timeout.value()
        )
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._connection_finished)
        self._worker.finished.connect(self._thread.quit)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def _connection_finished(self, success: bool, message: str) -> None:
        self.status.setText(message)
        if success:
            QMessageBox.information(self, "连接测试", message)
        else:
            QMessageBox.warning(self, "连接测试", message)
