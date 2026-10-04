"""Desktop configuration helpers.

The desktop shell edits the repository ``.env`` file directly.  This module
keeps that operation dependency free and preserves comments and unknown keys so
settings managed by the server or OpenClaw are not lost.
"""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from pathlib import Path

_KEY = re.compile(
    r"^(?P<prefix>\s*(?:export\s+)?)?(?P<key>[A-Za-z_][A-Za-z0-9_]*)(?P<rest>\s*=.*)$"
)


def _env_path(path: str | Path | None = None) -> Path:
    return Path(path or (Path.cwd() / ".env")).expanduser()


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1]
        # Keep backslashes literal: they are common in Windows paths.
        return value.replace('\\"', '"')
    # dotenv treats an unquoted # preceded by whitespace as a comment.
    return re.sub(r"\s+#.*$", "", value).strip()


def read_env(path: str | Path | None = None) -> dict[str, str]:
    """Read a dotenv file without modifying ``os.environ``."""
    target = _env_path(path)
    if not target.is_file():
        return {}
    result: dict[str, str] = {}
    for line in target.read_text(encoding="utf-8").splitlines():
        match = _KEY.match(line)
        if match:
            result[match.group("key")] = _unquote(match.group("rest")[1:])
    return result


def _format_value(value: object) -> str:
    text = str(value)
    if not text:
        return '""'
    # Quoting avoids accidental comments and keeps Windows paths intact.
    if re.search(r"[\s#'\"]", text):
        return '"' + text.replace('"', '\\"') + '"'
    return text


def update_env(path: str | Path, updates: Mapping[str, object]) -> None:
    """Update keys in a dotenv file while preserving all unrelated lines."""
    target = _env_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    had_file = target.is_file()
    raw = target.read_text(encoding="utf-8") if had_file else ""
    newline = "\r\n" if "\r\n" in raw else "\n"
    lines = raw.splitlines()
    pending = {str(k): v for k, v in updates.items()}
    output: list[str] = []
    for line in lines:
        match = _KEY.match(line)
        if match and match.group("key") in pending:
            key = match.group("key")
            output.append(f"{key}={_format_value(pending.pop(key))}")
        else:
            output.append(line)
    if pending:
        if output and output[-1] != "":
            output.append("")
        output.extend(f"{key}={_format_value(value)}" for key, value in pending.items())
    content = newline.join(output)
    if output or had_file:
        content += newline
    target.write_text(content, encoding="utf-8", newline="")


def load_env(path: str | Path | None = None, *, override: bool = False) -> dict[str, str]:
    """Load dotenv values into the process and return the loaded mapping."""
    values = read_env(path)
    for key, value in values.items():
        if override or key not in os.environ:
            os.environ[key] = value
    return values


class ConfigStore:
    """Read and persist desktop provider settings in a project ``.env``."""

    def __init__(self, project_root: str | Path | None = None) -> None:
        self.project_root = (
            Path(project_root or Path(__file__).resolve().parents[2]).expanduser().resolve()
        )
        self.env_path = self.project_root / ".env"

    def load(self) -> dict[str, str]:
        return read_env(self.env_path)

    def get_provider_settings(self, provider: str | None = None) -> dict[str, str]:
        values = self.load()
        mode = values.get("CLAWBOT_DECISION_MODE", "deepseek").strip().lower()
        selected = (
            str(provider or ("openclaw" if mode in {"agent", "openclaw"} else "deepseek"))
            .strip()
            .lower()
        )
        prefix = "OPENCLAW" if selected in {"agent", "openclaw"} else "DEEPSEEK"
        names = {
            "api_key": f"CLAWBOT_{prefix}_API_KEY",
            "base_url": f"CLAWBOT_{prefix}_BASE_URL",
            "model": f"CLAWBOT_{prefix}_MODEL",
            "timeout": f"CLAWBOT_{prefix}_TIMEOUT_SEC",
        }
        result = {field: values.get(name, "") for field, name in names.items()}
        result["provider"] = "openclaw" if prefix == "OPENCLAW" else "deepseek"
        result["decision_mode"] = "agent" if prefix == "OPENCLAW" else "deepseek"
        if prefix == "DEEPSEEK":
            result["base_url"] = result["base_url"] or "https://api.deepseek.com"
            result["model"] = result["model"] or "deepseek-chat"
            result["timeout"] = result["timeout"] or "60"
        return result

    def save_provider_settings(
        self,
        provider: str,
        api_key: str,
        base_url: str,
        model: str,
        timeout: float | int,
    ) -> None:
        prefix = str(provider).strip().upper()
        update_env(
            self.env_path,
            {
                "CLAWBOT_DECISION_MODE": "agent"
                if str(provider).strip().lower() in {"agent", "openclaw"}
                else "deepseek",
                f"CLAWBOT_{prefix}_API_KEY": api_key,
                f"CLAWBOT_{prefix}_BASE_URL": base_url,
                f"CLAWBOT_{prefix}_MODEL": model,
                f"CLAWBOT_{prefix}_TIMEOUT_SEC": timeout,
            },
        )

    def build_backend_env(self) -> dict[str, str]:
        """Build backend process environment from OS values plus project dotenv."""
        environment = os.environ.copy()
        environment.update(self.load())
        # A first-run desktop install has no .env yet. Keep the backend's
        # default provider aligned with the settings page in that case.
        environment.setdefault("CLAWBOT_DECISION_MODE", "deepseek")
        environment.setdefault("CLAWBOT_DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        environment.setdefault("CLAWBOT_DEEPSEEK_MODEL", "deepseek-chat")
        environment.setdefault("CLAWBOT_DEEPSEEK_TIMEOUT_SEC", "60")
        src = str((self.project_root / "src").resolve())
        paths = [item for item in environment.get("PYTHONPATH", "").split(os.pathsep) if item]
        if src not in paths:
            paths.insert(0, src)
        environment["PYTHONPATH"] = os.pathsep.join(paths)
        return environment


# Explicit aliases make the small file useful to callers that call this a dotenv reader.
read_dotenv = read_env
update_dotenv = update_env
