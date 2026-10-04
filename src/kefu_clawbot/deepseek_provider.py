"""DeepSeek provider using the OpenAI-compatible chat completions API."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any

from .model_provider import ModelReply
from .models import IncomingEvent
from .openclaw_agent import build_default_reply_prompt


class DeepSeekProvider:
    name = "deepseek"

    def __init__(self, *, api_key: str, base_url: str, model: str, timeout_sec: float = 60.0) -> None:
        self.api_key = api_key.strip()
        self.base_url = base_url.rstrip("/")
        self.model = model.strip()
        self.timeout_sec = max(1.0, float(timeout_sec))
        if not self.api_key:
            raise ValueError("deepseek_api_key_required")
        if not self.base_url or not self.model:
            raise ValueError("deepseek_base_url_and_model_required")

    def build_messages(self, event: IncomingEvent, history: list[dict[str, str]] | None = None) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = [
            {"role": "system", "content": "你是电商客服，只输出简洁、礼貌、可直接发送给顾客的中文回复。"},
        ]
        for item in history or []:
            role = str(item.get("role") or "user").lower()
            if role not in {"user", "assistant"}:
                role = "user"
            content = str(item.get("content") or item.get("text") or "").strip()
            if content:
                messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": build_default_reply_prompt(event)})
        return messages

    def reply(self, event: IncomingEvent, *, history: list[dict[str, str]] | None = None) -> ModelReply:
        payload = {"model": self.model, "messages": self.build_messages(event, history), "temperature": 0.2}
        request = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_sec) as response:
                data: Any = json.loads(response.read().decode("utf-8"))
        except TimeoutError as exc:
            raise RuntimeError("deepseek_request_timeout") from exc
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"deepseek_http_error:{exc.code}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError("deepseek_connection_error") from exc
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise RuntimeError("deepseek_invalid_json_response") from exc
        try:
            text = str(data["choices"][0]["message"]["content"] or "").strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError("deepseek_invalid_response") from exc
        if not text:
            raise RuntimeError("deepseek_empty_reply")
        return ModelReply(text=text, session_key=event.session_key())
