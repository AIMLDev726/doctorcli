from __future__ import annotations

from dataclasses import dataclass

from doctorcli.domain.models import ProviderType


@dataclass(frozen=True)
class ProviderProfile:
    type: ProviderType
    label: str
    description: str
    base_url_hint: str
    api_key_required: bool
    local_first: bool = False


PROVIDER_PROFILES: tuple[ProviderProfile, ...] = (
    ProviderProfile(
        type=ProviderType.OPENAI,
        label="OpenAI",
        description="Official OpenAI Responses via chat-completions compatible streaming.",
        base_url_hint="https://api.openai.com",
        api_key_required=True,
    ),
    ProviderProfile(
        type=ProviderType.GEMINI,
        label="Gemini",
        description="Google Gemini with live model discovery and streaming chat.",
        base_url_hint="https://generativelanguage.googleapis.com",
        api_key_required=True,
    ),
    ProviderProfile(
        type=ProviderType.GROQ,
        label="Groq",
        description="Groq's OpenAI-compatible low-latency inference API.",
        base_url_hint="https://api.groq.com/openai/v1",
        api_key_required=True,
    ),
    ProviderProfile(
        type=ProviderType.CLAUDE,
        label="Claude",
        description="Anthropic Claude native Messages API with streamed content blocks.",
        base_url_hint="https://api.anthropic.com",
        api_key_required=True,
    ),
    ProviderProfile(
        type=ProviderType.OLLAMA,
        label="Ollama",
        description="Local Ollama runtime for on-device chat models.",
        base_url_hint="http://127.0.0.1:11434",
        api_key_required=False,
        local_first=True,
    ),
    ProviderProfile(
        type=ProviderType.LMSTUDIO,
        label="LM Studio",
        description="Local LM Studio server using OpenAI-compatible endpoints.",
        base_url_hint="http://127.0.0.1:1234/v1",
        api_key_required=False,
        local_first=True,
    ),
)


def get_provider_profile(provider_type: ProviderType) -> ProviderProfile:
    for profile in PROVIDER_PROFILES:
        if profile.type == provider_type:
            return profile
    raise KeyError(f"Unknown provider type: {provider_type}")
