from __future__ import annotations

from abc import ABC, abstractmethod

import httpx

from doctorcli.domain.models import ToolDefinition, ToolResult, ToolSettings
from doctorcli.exceptions import ConfigurationError


class ExternalTool(ABC):
    tool_name: str
    requires_api_key: bool = False

    @abstractmethod
    def definition(self) -> ToolDefinition:
        raise NotImplementedError

    @abstractmethod
    def execute(self, settings: ToolSettings, arguments: dict[str, object]) -> ToolResult:
        raise NotImplementedError

    def _client(self) -> httpx.Client:
        return httpx.Client(timeout=30)

    def _require_api_key(self, settings: ToolSettings) -> str:
        if settings.api_key is None or not settings.api_key.get_secret_value().strip():
            raise ConfigurationError(f"API key is not configured for tool '{self.tool_name}'.")
        return settings.api_key.get_secret_value().strip()
