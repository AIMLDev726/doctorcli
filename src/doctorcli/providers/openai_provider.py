from __future__ import annotations

from doctorcli.domain.models import ProviderType
from doctorcli.providers.openai_compatible import OpenAICompatibleProvider


class OpenAIProvider(OpenAICompatibleProvider):
    provider_name = "OpenAI"
    provider_type = ProviderType.OPENAI
    default_base_url = "https://api.openai.com"
    requires_api_key = True
