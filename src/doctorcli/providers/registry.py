from __future__ import annotations

from doctorcli.domain.models import ProviderType
from doctorcli.providers.base import ProviderClient
from doctorcli.providers.claude_provider import ClaudeProvider
from doctorcli.providers.gemini_provider import GeminiProvider
from doctorcli.providers.groq_provider import GroqProvider
from doctorcli.providers.lmstudio_provider import LMStudioProvider
from doctorcli.providers.ollama_provider import OllamaProvider
from doctorcli.providers.openai_provider import OpenAIProvider


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[ProviderType, ProviderClient] = {
            ProviderType.OPENAI: OpenAIProvider(),
            ProviderType.GEMINI: GeminiProvider(),
            ProviderType.GROQ: GroqProvider(),
            ProviderType.CLAUDE: ClaudeProvider(),
            ProviderType.OLLAMA: OllamaProvider(),
            ProviderType.LMSTUDIO: LMStudioProvider(),
        }

    def get(self, provider: ProviderType) -> ProviderClient:
        return self._providers[provider]

    def items(self) -> list[tuple[ProviderType, ProviderClient]]:
        return list(self._providers.items())
