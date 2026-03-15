from __future__ import annotations

from doctorcli.domain.models import ToolDefinition, ToolResult, ToolSettings, ToolSource
from doctorcli.tools.base import ExternalTool


class TavilyTool(ExternalTool):
    tool_name = "tavily_search"
    requires_api_key = True

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.tool_name,
            description="Search the web for current medical, scientific, or factual context using Tavily.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query to run with Tavily.",
                    }
                },
                "required": ["query"],
            },
        )

    def execute(self, settings: ToolSettings, arguments: dict[str, object]) -> ToolResult:
        query = str(arguments.get("query", "")).strip()
        if not query:
            return ToolResult(
                tool_call_id="",
                name=self.tool_name,
                query=query,
                content="Tavily search skipped: query was empty.",
            )

        api_key = self._require_api_key(settings)
        payload = {
            "api_key": api_key,
            "query": query,
            "max_results": 5,
            "search_depth": "basic",
            "include_answer": True,
        }
        with self._client() as client:
            response = client.post("https://api.tavily.com/search", json=payload)
            response.raise_for_status()
            data = response.json()

        lines: list[str] = []
        sources: list[ToolSource] = []
        answer = data.get("answer")
        if answer:
            lines.append(f"Answer: {answer}")
        for item in data.get("results", [])[:5]:
            title = item.get("title", "Untitled")
            url = item.get("url", "")
            content = str(item.get("content", "")).replace("\n", " ").strip()
            sources.append(ToolSource(title=title, url=url or None, snippet=content[:240] or None))
            lines.append(f"- {title} | {url} | {content[:240]}")
        if not lines:
            lines.append(f"No Tavily web results found for '{query}'.")

        return ToolResult(
            tool_call_id="",
            name=self.tool_name,
            query=query,
            content="\n".join(lines),
            sources=sources,
        )
