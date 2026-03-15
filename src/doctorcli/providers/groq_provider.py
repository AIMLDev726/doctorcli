from __future__ import annotations

from doctorcli.domain.models import ProviderType
from doctorcli.providers.openai_compatible import OpenAICompatibleProvider


class GroqProvider(OpenAICompatibleProvider):
    provider_name = "Groq"
    provider_type = ProviderType.GROQ
    default_base_url = "https://api.groq.com/openai/v1"
    requires_api_key = True
