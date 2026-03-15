from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from doctorcli.domain.models import ChatRequest, ModelInfo, ProviderSettings, ProviderType, StreamEvent, StreamEventType
from doctorcli.providers.base import ProviderClient, final_text_event, iter_json_lines, parse_created_timestamp


class OllamaProvider(ProviderClient):
    provider_name = "Ollama"
    default_base_url = "http://127.0.0.1:11434"

    def list_models(self, settings: ProviderSettings) -> list[ModelInfo]:
        with self._client() as client:
            response = client.get(f"{self._base_url(settings)}/api/tags")
            if response.status_code >= 400:
                raise self._parse_error(response)
            payload = response.json()

        models: list[ModelInfo] = []
        for item in payload.get("models", []):
            model_id = item.get("model") or item.get("name")
            if not model_id:
                continue
            details = item.get("details") or {}
            models.append(
                ModelInfo(
                    id=model_id,
                    provider=ProviderType.OLLAMA,
                    name=item.get("name") or model_id,
                    description=details.get("family") or details.get("format") or "Local Ollama model",
                    created=parse_created_timestamp(item.get("modified_at")),
                    thinking_supported="think" in model_id.lower() or "reason" in model_id.lower(),
                    raw=item,
                )
            )
        models.sort(key=lambda model: model.created or parse_created_timestamp(0), reverse=True)
        return models

    def stream_chat(self, settings: ProviderSettings, request: ChatRequest) -> Iterator[StreamEvent]:
        payload = {
            "model": request.model,
            "stream": True,
            "messages": [
                {"role": "system", "content": request.system_prompt},
                *[
                    {"role": message.role.value, "content": message.content}
                    for message in request.messages
                ],
            ],
        }

        with self._client() as client:
            with client.stream("POST", f"{self._base_url(settings)}/api/chat", json=payload) as response:
                if response.status_code >= 400:
                    raise self._parse_error(response)
                for item in iter_json_lines(response):
                    yield from self._stream_events_from_payload(item)
        yield final_text_event()

    def _stream_events_from_payload(self, payload: dict[str, Any]) -> Iterator[StreamEvent]:
        message = payload.get("message") or {}
        thinking = message.get("thinking") or payload.get("thinking")
        if thinking:
            yield StreamEvent(type=StreamEventType.REASONING, text=str(thinking), raw=payload)
        content = message.get("content") or payload.get("response")
        if content:
            yield StreamEvent(type=StreamEventType.CONTENT, text=str(content), raw=payload)

    def _base_url(self, settings: ProviderSettings) -> str:
        return (settings.base_url or self.default_base_url).rstrip("/")
