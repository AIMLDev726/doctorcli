from __future__ import annotations

from doctorcli.domain.models import AppSettings, ModelInfo, ProviderSettings, ProviderType, ToolSettings, ToolType, utc_now
from doctorcli.storage.filesystem import AppFilesystem


class SettingsStore:
    def __init__(self, filesystem: AppFilesystem) -> None:
        self.filesystem = filesystem

    def load(self) -> AppSettings:
        self.filesystem.ensure_layout()
        payload = self.filesystem.read_json(self.filesystem.settings_path, default={})
        if not payload:
            settings = AppSettings()
            self.save(settings)
            return settings

        settings = AppSettings.model_validate(payload)
        changed = False
        for provider in ProviderType:
            if provider not in settings.providers:
                settings.providers[provider] = ProviderSettings()
                changed = True
        for tool in ToolType:
            if tool not in settings.tools:
                settings.tools[tool] = ToolSettings()
                changed = True
        if changed:
            self.save(settings)
        return settings

    def save(self, settings: AppSettings) -> None:
        self.filesystem.ensure_layout()
        self.filesystem.write_json(
            self.filesystem.settings_path,
            settings.model_dump(mode="json", exclude_none=True),
        )

    def update_provider(self, provider: ProviderType, data: ProviderSettings) -> AppSettings:
        settings = self.load()
        settings.providers[provider] = data
        self.save(settings)
        return settings

    def update_tool(self, tool: ToolType, data: ToolSettings) -> AppSettings:
        settings = self.load()
        settings.tools[tool] = data
        self.save(settings)
        return settings

    def update_model_cache(
        self,
        provider: ProviderType,
        models: list[ModelInfo],
    ) -> AppSettings:
        settings = self.load()
        provider_settings = settings.providers[provider]
        provider_settings.model_cache = models
        provider_settings.model_cache_updated_at = utc_now()
        self.save(settings)
        return settings
