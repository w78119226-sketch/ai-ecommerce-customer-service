from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication, QLineEdit

from kefu_desktop.config import ConfigStore
from kefu_desktop.pages.ai_settings import AISettingsPage, _ConnectionWorker


class _Response:
    status = 200
    headers = {}

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps({"choices": [{"message": {"content": "ok"}}]}).encode()


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_api_key_field_is_password_hidden_and_defaults(tmp_path: Path) -> None:
    _app()
    page = AISettingsPage(ConfigStore(tmp_path))
    assert page.api_key.echoMode() == QLineEdit.EchoMode.Password
    assert page.base_url.text() == "https://api.deepseek.com"
    assert page.model.text() == "deepseek-chat"
    assert page.timeout.value() == 60


def test_connection_worker_makes_real_compatible_request_without_logging_key() -> None:
    worker = _ConnectionWorker("secret-key", "https://example.test/v1", "deepseek-chat", 4)
    messages: list[tuple[bool, str]] = []
    worker.finished.connect(lambda ok, message: messages.append((ok, message)))
    with patch(
        "kefu_desktop.pages.ai_settings.urllib.request.urlopen", return_value=_Response()
    ) as mocked:
        worker.run()
    assert messages == [(True, "连接成功")]
    request = mocked.call_args.args[0]
    assert request.full_url.endswith("/v1/chat/completions")
    assert request.get_header("Authorization") == "Bearer secret-key"
    assert "secret-key" not in request.data.decode()
