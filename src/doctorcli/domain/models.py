from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_serializer

from doctorcli.constants import SETTINGS_VERSION


def utc_now() -> datetime:
    return datetime.now(UTC)


class ProviderType(str, Enum):
    OPENAI = "openai"
    GEMINI = "gemini"
    GROQ = "groq"
    CLAUDE = "claude"
    OLLAMA = "ollama"
    LMSTUDIO = "lmstudio"


class ToolType(str, Enum):
    WIKIPEDIA = "wikipedia"
    TAVILY = "tavily"


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class AgentProfile(BaseModel):
    id: str
    name: str
    specialty: str
    summary: str
    communication_style: str
    system_prompt: str


class ModelInfo(BaseModel):
    id: str
    provider: ProviderType
    name: str
    description: str | None = None
    created: datetime | None = None
    context_window: int | None = None
    max_output_tokens: int | None = None
    thinking_supported: bool = False
    raw: dict[str, Any] = Field(default_factory=dict)


class ProviderSettings(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    api_key: SecretStr | None = None
    base_url: str | None = None
    enabled: bool = True
    default_model: str | None = None
    model_cache: list[ModelInfo] = Field(default_factory=list)
    model_cache_updated_at: datetime | None = None

    @field_serializer("api_key", when_used="json")
    def serialize_api_key(self, value: SecretStr | None) -> str | None:
        if value is None:
            return None
        return value.get_secret_value()

    def masked_api_key(self) -> str:
        if self.api_key is None:
            return "Not configured"
        value = self.api_key.get_secret_value()
        if len(value) <= 8:
            return "*" * len(value)
        return f"{value[:4]}...{value[-4:]}"


class ToolSettings(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    enabled: bool = True
    api_key: SecretStr | None = None

    @field_serializer("api_key", when_used="json")
    def serialize_api_key(self, value: SecretStr | None) -> str | None:
        if value is None:
            return None
        return value.get_secret_value()

    def masked_api_key(self) -> str:
        if self.api_key is None:
            return "Not configured"
        value = self.api_key.get_secret_value()
        if len(value) <= 8:
            return "*" * len(value)
        return f"{value[:4]}...{value[-4:]}"


class AppSettings(BaseModel):
    version: int = SETTINGS_VERSION
    providers: dict[ProviderType, ProviderSettings] = Field(
        default_factory=lambda: {provider: ProviderSettings() for provider in ProviderType}
    )
    tools: dict[ToolType, ToolSettings] = Field(
        default_factory=lambda: {tool: ToolSettings() for tool in ToolType}
    )


class SessionMessage(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    role: MessageRole
    content: str
    reasoning: str | None = None
    tool_name: str | None = None
    tool_call_id: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class SessionMetadata(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    reason: str
    agent_id: str
    provider: ProviderType
    model: str
    tools: list[ToolType] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class ChatSession(BaseModel):
    metadata: SessionMetadata
    messages: list[SessionMessage] = Field(default_factory=list)

    def touch(self) -> None:
        self.metadata.updated_at = utc_now()


class SessionPreview(BaseModel):
    id: str
    name: str
    reason: str
    agent_id: str
    provider: ProviderType
    model: str
    created_at: datetime
    updated_at: datetime
    message_count: int


class ChatRequest(BaseModel):
    model: str
    system_prompt: str
    messages: list[SessionMessage]


class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any]


class ToolCall(BaseModel):
    id: str
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolSource(BaseModel):
    title: str
    url: str | None = None
    snippet: str | None = None


class ToolResult(BaseModel):
    tool_call_id: str
    name: str
    content: str
    query: str | None = None
    sources: list[ToolSource] = Field(default_factory=list)


class ToolChatResult(BaseModel):
    content: str = ""
    reasoning: str | None = None
    tool_calls: list[ToolCall] = Field(default_factory=list)


class StreamEventType(str, Enum):
    CONTENT = "content"
    REASONING = "reasoning"
    TOOL = "tool"
    COMPLETE = "complete"


class StreamEvent(BaseModel):
    type: StreamEventType
    text: str = ""
    raw: dict[str, Any] = Field(default_factory=dict)
