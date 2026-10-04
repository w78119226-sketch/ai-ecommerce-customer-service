"""Model provider abstractions used by the decision service."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .models import IncomingEvent
from .openclaw_agent import OpenClawAgentInvoker, OpenClawReply, build_default_reply_prompt


@dataclass(frozen=True)
class ModelReply:
    text: str
    session_key: str


class ModelProvider(Protocol):
    name: str

    def reply(self, event: IncomingEvent, *, history: list[dict[str, str]] | None = None) -> ModelReply:
        ...


class OpenClawProvider:
    name = "openclaw"

    def __init__(self, invoker: OpenClawAgentInvoker) -> None:
        self.invoker = invoker

    def reply(self, event: IncomingEvent, *, history: list[dict[str, str]] | None = None) -> ModelReply:
        _ = history
        result: OpenClawReply = self.invoker.ask(event)
        return ModelReply(text=result.text, session_key=result.session_key)
