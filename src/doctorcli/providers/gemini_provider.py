from __future__ import annotations

import json
from collections.abc import Callable, Iterator
from typing import Any

from doctorcli.domain.models import ChatRequest, MessageRole, ModelInfo, ProviderSettings, ProviderType, StreamEvent, StreamEventType, ToolCall, ToolChatResult, ToolDefinition, ToolResult
from doctorcli.providers.base import ProviderClient, extract_text, final_text_event, iter_sse_payloads, parse_created_timestamp


class GeminiProvider(ProviderClient):
    provider_name = "Gemini"
    default_base_url = "https://generativelanguage.googleapis.com"

    def list_models(self, settings: ProviderSettings) -> list[ModelInfo]:
        api_key = self._require_api_key(settings)
        models: list[ModelInfo] = []
        page_token: str | None = None

        with self._client() as client:
            while True:
                params = {"key": api_key, "pageSize": 200}
                if page_token:
                    params["pageToken"] = page_token
                response = client.get(f"{self._native_base_url(settings)}/v1beta/models", params=params)
                if response.status_code >= 400:
                    raise self._parse_error(response)
                payload = response.json()
                for item in payload.get("models", []):
                    supported_methods = item.get("supportedGenerationMethods") or []
                    if "generateContent" not in supported_methods and "streamGenerateContent" not in supported_methods:
                        continue
                    raw_name = item.get("name", "")
                    model_id = raw_name.removeprefix("models/")
                    if not model_id:
                        continue
                    models.append(
                        ModelInfo(
                            id=model_id,
                            provider=ProviderType.GEMINI,
                            name=item.get("displayName") or model_id,
                            description=item.get("description"),
                            created=parse_created_timestamp(item.get("createTime") or item.get("updateTime")),
                            context_window=item.get("inputTokenLimit"),
                            max_output_tokens=item.get("outputTokenLimit"),
                            thinking_supported=self._thinking_supported(model_id, item),
                            raw=item,
                        )
                    )
                page_token = payload.get("nextPageToken")
                if not page_token:
                    break

        models.sort(key=lambda model: model.created or parse_created_timestamp(0), reverse=True)
        return models

    def stream_chat(self, settings: ProviderSettings, request: ChatRequest) -> Iterator[StreamEvent]:
        api_key = self._require_api_key(settings)
        payload = {"model": request.model, "stream": True, "messages": self._request_messages(request)}

        with self._client() as client:
            with client.stream("POST", f"{self._chat_base_url(settings)}/chat/completions", headers=self._headers(api_key), json=payload) as response:
                if response.status_code >= 400:
                    raise self._parse_error(response)
                for item in iter_sse_payloads(response):
                    yield from self._stream_events_from_payload(item)
        yield final_text_event()

    def run_with_tools(
        self,
        settings: ProviderSettings,
        request: ChatRequest,
        tools: list[ToolDefinition],
        tool_executor: Callable[[list[ToolCall]], list[ToolResult]],
    ) -> ToolChatResult:
        api_key = self._require_api_key(settings)
        messages: list[dict[str, Any]] = self._request_messages(request)
        tool_payload = [
            {"type": "function", "function": {"name": tool.name, "description": tool.description, "parameters": tool.parameters}}
            for tool in tools
        ]

        with self._client() as client:
            for _ in range(3):
                response = client.post(
                    f"{self._chat_base_url(settings)}/chat/completions",
                    headers=self._headers(api_key),
                    json={"model": request.model, "stream": False, "messages": messages, "tools": tool_payload, "tool_choice": "auto"},
                )
                if response.status_code >= 400:
                    raise self._parse_error(response)
                payload = response.json()
                message = (payload.get("choices") or [{}])[0].get("message") or {}
                tool_calls = self._parse_tool_calls(message)
                if not tool_calls:
                    return ToolChatResult(content=extract_text(message.get("content")), reasoning=extract_text(message.get("reasoning")) or None, tool_calls=[])

                messages.append(
                    {
                        "role": "assistant",
                        "content": extract_text(message.get("content")) or "",
                        "tool_calls": [
                            {"id": call.id, "type": "function", "function": {"name": call.name, "arguments": json.dumps(call.arguments)}}
                            for call in tool_calls
                        ],
                    }
                )
                tool_results = tool_executor(tool_calls)
                for result in tool_results:
                    messages.append({"role": "tool", "tool_call_id": result.tool_call_id, "content": result.content})
            raise RuntimeError("Tool loop exceeded maximum iterations.")

    def _stream_events_from_payload(self, payload: dict[str, Any]) -> Iterator[StreamEvent]:
        choices = payload.get("choices") or []
        if not choices:
            return
        delta = choices[0].get("delta") or {}
        reasoning = extract_text(delta.get("reasoning")) or extract_text(delta.get("reasoning_content")) or extract_text(delta.get("thinking"))
        if reasoning:
            yield StreamEvent(type=StreamEventType.REASONING, text=reasoning, raw=payload)
        content = extract_text(delta.get("content"))
        if content:
            yield StreamEvent(type=StreamEventType.CONTENT, text=content, raw=payload)

    def _parse_tool_calls(self, message: dict[str, Any]) -> list[ToolCall]:
        calls: list[ToolCall] = []
        for item in message.get("tool_calls") or []:
            function = item.get("function") or {}
            arguments = function.get("arguments") or "{}"
            if isinstance(arguments, str):
                try:
                    parsed_arguments = json.loads(arguments)
                except json.JSONDecodeError:
                    parsed_arguments = {"raw": arguments}
            else:
                parsed_arguments = arguments
            calls.append(ToolCall(id=item.get("id", ""), name=function.get("name", ""), arguments=parsed_arguments or {}))
        return calls

    def _request_messages(self, request: ChatRequest) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = [{"role": MessageRole.SYSTEM.value, "content": request.system_prompt}]
        for message in request.messages:
            entry = {"role": message.role.value, "content": message.content}
            if message.role == MessageRole.TOOL and message.tool_call_id:
                entry["tool_call_id"] = message.tool_call_id
            messages.append(entry)
        return messages

    def _headers(self, api_key: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", "Accept": "text/event-stream"}

    def _native_base_url(self, settings: ProviderSettings) -> str:
        base = (settings.base_url or self.default_base_url).rstrip("/")
        if base.endswith("/openai"):
            return base[: -len("/openai")]
        return base

    def _chat_base_url(self, settings: ProviderSettings) -> str:
        base = (settings.base_url or self.default_base_url).rstrip("/")
        if base.endswith("/openai"):
            return base
        return f"{base}/v1beta/openai"

    def _thinking_supported(self, model_id: str, payload: dict[str, Any]) -> bool:
        value = model_id.lower()
        description = str(payload.get("description", "")).lower()
        return "thinking" in value or "reason" in value or "thinking" in description or "2.5-pro" in value
