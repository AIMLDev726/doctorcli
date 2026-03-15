from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from typing import Any

import httpx

from doctorcli.constants import DEFAULT_TIMEOUT_SECONDS
from doctorcli.domain.models import ChatRequest, ModelInfo, ProviderSettings, StreamEvent, StreamEventType, ToolCall, ToolChatResult, ToolDefinition, ToolResult
from doctorcli.exceptions import ConfigurationError, ProviderError


class ProviderClient(ABC):
    provider_name: str

    def __init__(self, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> None:
        self.timeout = timeout

    @abstractmethod
    def list_models(self, settings: ProviderSettings) -> list[ModelInfo]:
        raise NotImplementedError

    @abstractmethod
    def stream_chat(self, settings: ProviderSettings, request: ChatRequest) -> Iterator[StreamEvent]:
        raise NotImplementedError

    def run_with_tools(
        self,
        settings: ProviderSettings,
        request: ChatRequest,
        tools: list[ToolDefinition],
        tool_executor: Callable[[list[ToolCall]], list[ToolResult]],
    ) -> ToolChatResult:
        raise ProviderError(f"Tool calling is not available for provider '{self.provider_name}'.")

    def _require_api_key(self, settings: ProviderSettings) -> str:
        if settings.api_key is None or not settings.api_key.get_secret_value().strip():
            raise ConfigurationError(f"API key is not configured for {self.provider_name}.")
        return settings.api_key.get_secret_value().strip()

    def _optional_api_key(self, settings: ProviderSettings) -> str | None:
        if settings.api_key is None:
            return None
        value = settings.api_key.get_secret_value().strip()
        return value or None

    def _client(self) -> httpx.Client:
        return httpx.Client(timeout=self.timeout)

    def _parse_error(self, response: httpx.Response) -> ProviderError:
        try:
            payload = response.json()
        except ValueError:
            payload = response.text
        return ProviderError(
            f"{self.provider_name} request failed with status {response.status_code}: {payload}"
        )


def parse_created_timestamp(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=UTC)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return None


def extract_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        chunks: list[str] = []
        for item in value:
            if isinstance(item, str):
                chunks.append(item)
            elif isinstance(item, dict):
                text = item.get("text") or item.get("content") or item.get("reasoning") or item.get("thinking")
                if text:
                    chunks.append(str(text))
        return "".join(chunks)
    if isinstance(value, dict):
        text = value.get("text") or value.get("content") or value.get("reasoning") or value.get("thinking")
        return "" if text is None else str(text)
    return str(value)


def iter_sse_payloads(response: httpx.Response) -> Iterator[dict[str, Any]]:
    event_name: str | None = None
    data_lines: list[str] = []

    for raw_line in response.iter_lines():
        line = raw_line.strip()
        if not line:
            if not data_lines:
                event_name = None
                continue
            joined = "\n".join(data_lines)
            data_lines = []
            if joined == "[DONE]":
                break
            try:
                payload = json.loads(joined)
            except json.JSONDecodeError:
                event_name = None
                continue
            if event_name:
                payload.setdefault("_event", event_name)
            yield payload
            event_name = None
            continue

        if line.startswith(":"):
            continue
        if line.startswith("event:"):
            event_name = line.removeprefix("event:").strip()
            continue
        if line.startswith("data:"):
            data_lines.append(line.removeprefix("data:").strip())


def iter_json_lines(response: httpx.Response) -> Iterator[dict[str, Any]]:
    for raw_line in response.iter_lines():
        line = raw_line.strip()
        if not line:
            continue
        try:
            yield json.loads(line)
        except json.JSONDecodeError:
            continue


def final_text_event() -> StreamEvent:
    return StreamEvent(type=StreamEventType.COMPLETE)
