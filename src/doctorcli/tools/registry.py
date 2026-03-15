from __future__ import annotations

from doctorcli.domain.models import ToolType
from doctorcli.tools.base import ExternalTool
from doctorcli.tools.tavily_tool import TavilyTool
from doctorcli.tools.wikipedia_tool import WikipediaTool


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[ToolType, ExternalTool] = {
            ToolType.WIKIPEDIA: WikipediaTool(),
            ToolType.TAVILY: TavilyTool(),
        }

    def get(self, tool_type: ToolType) -> ExternalTool:
        return self._tools[tool_type]

    def items(self) -> list[tuple[ToolType, ExternalTool]]:
        return list(self._tools.items())
