from __future__ import annotations

from doctorcli.domain.models import ProviderType
from doctorcli.providers.openai_compatible import OpenAICompatibleProvider


class LMStudioProvider(OpenAICompatibleProvider):
    provider_name = "LM Studio"
    provider_type = ProviderType.LMSTUDIO
    default_base_url = "http://127.0.0.1:1234/v1"
    requires_api_key = False
