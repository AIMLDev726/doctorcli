from __future__ import annotations

import re
from urllib.parse import quote

from doctorcli.domain.models import ToolDefinition, ToolResult, ToolSettings, ToolSource
from doctorcli.tools.base import ExternalTool


STRIP_HTML_RE = re.compile(r"<[^>]+>")


class WikipediaTool(ExternalTool):
    tool_name = "wikipedia_lookup"
    requires_api_key = False

    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name=self.tool_name,
            description="Search Wikipedia for a medical concept, condition, symptom, medication, or health topic.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The topic or term to search for on Wikipedia.",
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
                content="Wikipedia lookup skipped: query was empty.",
            )

        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": 3,
            "utf8": 1,
            "format": "json",
            "origin": "*",
        }
        with self._client() as client:
            response = client.get("https://en.wikipedia.org/w/api.php", params=params)
            response.raise_for_status()
            payload = response.json()

        results = payload.get("query", {}).get("search", [])
        sources: list[ToolSource] = []
        if not results:
            content = f"No Wikipedia matches found for '{query}'."
        else:
            lines: list[str] = []
            for item in results:
                title = item.get("title", "Untitled")
                snippet = STRIP_HTML_RE.sub("", item.get("snippet", "")).replace("\n", " ").strip()
                url = f"https://en.wikipedia.org/wiki/{quote(title.replace(' ', '_'))}"
                sources.append(ToolSource(title=title, url=url, snippet=snippet or None))
                lines.append(f"- {title}: {snippet}")
            content = "Wikipedia search results:\n" + "\n".join(lines)

        return ToolResult(
            tool_call_id="",
            name=self.tool_name,
            query=query,
            content=content,
            sources=sources,
        )
