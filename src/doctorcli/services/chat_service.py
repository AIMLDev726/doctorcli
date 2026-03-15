from __future__ import annotations

import re
from collections.abc import Iterator

from doctorcli.agents import get_agent
from doctorcli.domain.models import (
    ChatSession,
    ProviderSettings,
    StreamEvent,
    StreamEventType,
    ToolCall,
    ToolResult,
    ToolSettings,
    ToolType,
)
from doctorcli.exceptions import DoctorCliError
from doctorcli.providers.registry import ProviderRegistry
from doctorcli.services.memory_service import MemoryService
from doctorcli.services.session_service import SessionService
from doctorcli.storage.settings_store import SettingsStore
from doctorcli.tools.base import ExternalTool
from doctorcli.tools.registry import ToolRegistry


THINK_BLOCK_RE = re.compile(r"<think>(.*?)</think>", re.IGNORECASE | re.DOTALL)
WORD_CHUNK_RE = re.compile(r"\S+\s*")
TOOL_GUIDANCE = (
    "\n\nTool use policy: If the user asks to check online, search the web, verify current facts, or if external lookup would "
    "materially improve accuracy, use the available tools before answering. When tools are attached, prefer using them over "
    "guessing current information."
)


class ChatService:
    def __init__(
        self,
        provider_registry: ProviderRegistry,
        memory_service: MemoryService,
        session_service: SessionService,
        settings_store: SettingsStore,
        tool_registry: ToolRegistry,
    ) -> None:
        self.provider_registry = provider_registry
        self.memory_service = memory_service
        self.session_service = session_service
        self.settings_store = settings_store
        self.tool_registry = tool_registry

    def stream_turn(
        self,
        session: ChatSession,
        provider_settings: ProviderSettings,
        user_input: str,
    ) -> Iterator[StreamEvent]:
        agent = get_agent(session.metadata.agent_id)
        self.session_service.add_user_message(session, user_input)
        request = self.memory_service.build_request(session, agent)
        provider = self.provider_registry.get(session.metadata.provider)
        active_tools = self._resolve_session_tools(session)
        if active_tools:
            request.system_prompt = f"{request.system_prompt}{TOOL_GUIDANCE}"

        def generator() -> Iterator[StreamEvent]:
            if active_tools:
                tool_results: list[ToolResult] = []
                try:
                    result = provider.run_with_tools(
                        provider_settings,
                        request,
                        [tool.definition() for _, tool, _ in active_tools],
                        lambda calls: self._execute_tool_calls(calls, active_tools, tool_results),
                    )
                    for tool_result in tool_results:
                        yield StreamEvent(
                            type=StreamEventType.TOOL,
                            text=tool_result.content,
                            raw={
                                "name": tool_result.name,
                                "query": tool_result.query,
                                "content": tool_result.content,
                                "sources": [source.model_dump(mode="json", exclude_none=True) for source in tool_result.sources],
                            },
                        )
                    content, reasoning = self._normalize_outputs(result.content, result.reasoning or "")
                    yield from self._emit_synthetic_stream(reasoning, content)
                    self.session_service.add_assistant_message(session, content, reasoning)
                    return
                except DoctorCliError as exc:
                    if not self._should_fallback_without_tools(exc):
                        raise

            content_parts: list[str] = []
            reasoning_parts: list[str] = []
            for event in provider.stream_chat(provider_settings, request):
                if event.type == StreamEventType.CONTENT:
                    content_parts.append(event.text)
                elif event.type == StreamEventType.REASONING:
                    reasoning_parts.append(event.text)
                yield event

            content, reasoning = self._normalize_outputs(
                "".join(content_parts),
                "".join(reasoning_parts),
            )
            self.session_service.add_assistant_message(session, content, reasoning)

        return generator()

    def _resolve_session_tools(
        self,
        session: ChatSession,
    ) -> list[tuple[ToolType, ExternalTool, ToolSettings]]:
        settings = self.settings_store.load()
        resolved: list[tuple[ToolType, ExternalTool, ToolSettings]] = []
        for tool_type in session.metadata.tools:
            tool_settings = settings.tools.get(tool_type)
            if tool_settings is None or not tool_settings.enabled:
                continue
            tool = self.tool_registry.get(tool_type)
            if tool.requires_api_key:
                if tool_settings.api_key is None or not tool_settings.api_key.get_secret_value().strip():
                    continue
            resolved.append((tool_type, tool, tool_settings))
        return resolved

    def _execute_tool_calls(
        self,
        tool_calls: list[ToolCall],
        active_tools: list[tuple[ToolType, ExternalTool, ToolSettings]],
        collected_results: list[ToolResult],
    ) -> list[ToolResult]:
        available = {tool.tool_name: (tool, settings) for _, tool, settings in active_tools}
        results: list[ToolResult] = []
        for call in tool_calls:
            mapped = available.get(call.name)
            if mapped is None:
                result = ToolResult(
                    tool_call_id=call.id,
                    name=call.name,
                    query=str(call.arguments.get("query", "")).strip() or None,
                    content=f"Tool '{call.name}' is not available in this session.",
                )
                results.append(result)
                collected_results.append(result)
                continue
            tool, tool_settings = mapped
            try:
                result = tool.execute(tool_settings, call.arguments)
                result.tool_call_id = call.id
                result.name = call.name
                if result.query is None:
                    result.query = str(call.arguments.get("query", "")).strip() or None
            except Exception as exc:  # pragma: no cover
                result = ToolResult(
                    tool_call_id=call.id,
                    name=call.name,
                    query=str(call.arguments.get("query", "")).strip() or None,
                    content=f"Tool '{call.name}' failed: {exc}",
                )
            results.append(result)
            collected_results.append(result)
        return results

    def _emit_synthetic_stream(self, reasoning: str | None, content: str) -> Iterator[StreamEvent]:
        if reasoning:
            for chunk in self._chunk_text(reasoning):
                yield StreamEvent(type=StreamEventType.REASONING, text=chunk)
        for chunk in self._chunk_text(content):
            yield StreamEvent(type=StreamEventType.CONTENT, text=chunk)
        yield StreamEvent(type=StreamEventType.COMPLETE)

    def _chunk_text(self, value: str) -> list[str]:
        return [match.group(0) for match in WORD_CHUNK_RE.finditer(value)] or ([value] if value else [])

    def _should_fallback_without_tools(self, exc: DoctorCliError) -> bool:
        message = str(exc).lower()
        hints = (
            "tool calling",
            "tool call",
            "tool_choice",
            "tool_calls",
            "function call",
            "functions are not supported",
            "does not support tools",
            "does not support function",
            "unsupported",
            "not available for provider",
            "tools are not supported",
        )
        return any(hint in message for hint in hints)

    def _normalize_outputs(self, content: str, reasoning: str) -> tuple[str, str | None]:
        extracted: list[str] = []

        def replace(match: re.Match[str]) -> str:
            extracted.append(match.group(1).strip())
            return ""

        cleaned_content = THINK_BLOCK_RE.sub(replace, content).strip()
        combined_reasoning = reasoning.strip()
        if extracted:
            tag_reasoning = "\n\n".join(item for item in extracted if item)
            combined_reasoning = (
                f"{combined_reasoning}\n\n{tag_reasoning}".strip()
                if combined_reasoning
                else tag_reasoning
            )
        return cleaned_content, combined_reasoning or None
