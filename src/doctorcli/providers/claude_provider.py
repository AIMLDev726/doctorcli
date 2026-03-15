from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from doctorcli.domain.models import ChatRequest, ModelInfo, ProviderSettings, ProviderType, StreamEvent, StreamEventType
from doctorcli.providers.base import ProviderClient, final_text_event, iter_sse_payloads, parse_created_timestamp


class ClaudeProvider(ProviderClient):
    provider_name = "Claude"
    default_base_url = "https://api.anthropic.com"
    anthropic_version = "2023-06-01"
    default_max_tokens = 2048

    def list_models(self, settings: ProviderSettings) -> list[ModelInfo]:
        api_key = self._require_api_key(settings)
        with self._client() as client:
            response = client.get(
                f"{self._base_url(settings)}/v1/models",
                headers=self._headers(api_key),
            )
            if response.status_code >= 400:
                raise self._parse_error(response)
            payload = response.json()

        models: list[ModelInfo] = []
        for item in payload.get("data", []):
            model_id = item.get("id")
            if not model_id:
                continue
            display_name = item.get("display_name") or item.get("name") or model_id
            models.append(
                ModelInfo(
                    id=model_id,
                    provider=ProviderType.CLAUDE,
                    name=display_name,
                    description="Anthropic Claude model",
                    created=parse_created_timestamp(item.get("created_at")),
                    thinking_supported=any(token in model_id.lower() for token in ("opus", "sonnet", "thinking")),
                    raw=item,
                )
            )
        models.sort(key=lambda model: model.created or parse_created_timestamp(0), reverse=True)
        return models

    def stream_chat(self, settings: ProviderSettings, request: ChatRequest) -> Iterator[StreamEvent]:
        api_key = self._require_api_key(settings)
        payload = {
            "model": request.model,
            "max_tokens": self.default_max_tokens,
            "stream": True,
            "system": request.system_prompt,
            "messages": [
                {
                    "role": message.role.value,
                    "content": message.content,
                }
                for message in request.messages
                if message.role.value in {"user", "assistant"}
            ],
        }

        with self._client() as client:
            with client.stream(
                "POST",
                f"{self._base_url(settings)}/v1/messages",
                headers=self._headers(api_key),
                json=payload,
            ) as response:
                if response.status_code >= 400:
                    raise self._parse_error(response)
                for item in iter_sse_payloads(response):
                    yield from self._stream_events_from_payload(item)
        yield final_text_event()

    def _stream_events_from_payload(self, payload: dict[str, Any]) -> Iterator[StreamEvent]:
        payload_type = payload.get("type")
        if payload_type == "content_block_delta":
            delta = payload.get("delta") or {}
            delta_type = delta.get("type")
            if delta_type == "text_delta" and delta.get("text"):
                yield StreamEvent(type=StreamEventType.CONTENT, text=str(delta["text"]), raw=payload)
            elif delta_type == "thinking_delta" and delta.get("thinking"):
                yield StreamEvent(type=StreamEventType.REASONING, text=str(delta["thinking"]), raw=payload)
        elif payload_type == "content_block_start":
            block = payload.get("content_block") or {}
            if block.get("type") == "thinking" and block.get("thinking"):
                yield StreamEvent(type=StreamEventType.REASONING, text=str(block["thinking"]), raw=payload)
            elif block.get("type") == "text" and block.get("text"):
                yield StreamEvent(type=StreamEventType.CONTENT, text=str(block["text"]), raw=payload)

    def _headers(self, api_key: str) -> dict[str, str]:
        return {
            "x-api-key": api_key,
            "anthropic-version": self.anthropic_version,
            "content-type": "application/json",
            "accept": "text/event-stream",
        }

    def _base_url(self, settings: ProviderSettings) -> str:
        return (settings.base_url or self.default_base_url).rstrip("/")
