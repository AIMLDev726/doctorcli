from __future__ import annotations

from dataclasses import dataclass

from doctorcli.domain.models import ToolType


@dataclass(frozen=True)
class ToolProfile:
    type: ToolType
    label: str
    description: str
    category: str
    api_key_required: bool
    setup_hint: str


TOOL_PROFILES: tuple[ToolProfile, ...] = (
    ToolProfile(
        type=ToolType.WIKIPEDIA,
        label="Wikipedia",
        description="Reference lookup for symptoms, conditions, medications, and medical background topics.",
        category="Reference",
        api_key_required=False,
        setup_hint="No API key required.",
    ),
    ToolProfile(
        type=ToolType.TAVILY,
        label="Tavily",
        description="Live web search for current medical guidance, news, and factual updates.",
        category="Web search",
        api_key_required=True,
        setup_hint="Requires a Tavily API key.",
    ),
)


def get_tool_profile(tool_type: ToolType) -> ToolProfile:
    for profile in TOOL_PROFILES:
        if profile.type == tool_type:
            return profile
    raise KeyError(f"Unknown tool type: {tool_type}")
