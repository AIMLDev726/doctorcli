from __future__ import annotations

from dataclasses import dataclass

from rich.console import Console

from doctorcli.providers.registry import ProviderRegistry
from doctorcli.services.chat_service import ChatService
from doctorcli.services.memory_service import MemoryService
from doctorcli.services.scope_guard import ScopeGuardService
from doctorcli.services.session_service import SessionService
from doctorcli.storage.filesystem import AppFilesystem
from doctorcli.storage.session_store import SessionStore
from doctorcli.storage.settings_store import SettingsStore
from doctorcli.tools.registry import ToolRegistry
from doctorcli.ui.console import build_console


@dataclass(slots=True)
class ApplicationRuntime:
    console: Console
    filesystem: AppFilesystem
    settings_store: SettingsStore
    session_store: SessionStore
    provider_registry: ProviderRegistry
    tool_registry: ToolRegistry
    memory_service: MemoryService
    scope_guard: ScopeGuardService
    session_service: SessionService
    chat_service: ChatService


def build_runtime() -> ApplicationRuntime:
    console = build_console()
    filesystem = AppFilesystem()
    settings_store = SettingsStore(filesystem)
    session_store = SessionStore(filesystem)
    provider_registry = ProviderRegistry()
    tool_registry = ToolRegistry()
    memory_service = MemoryService()
    scope_guard = ScopeGuardService()
    session_service = SessionService(session_store)
    chat_service = ChatService(
        provider_registry=provider_registry,
        memory_service=memory_service,
        session_service=session_service,
        settings_store=settings_store,
        tool_registry=tool_registry,
    )
    return ApplicationRuntime(
        console=console,
        filesystem=filesystem,
        settings_store=settings_store,
        session_store=session_store,
        provider_registry=provider_registry,
        tool_registry=tool_registry,
        memory_service=memory_service,
        scope_guard=scope_guard,
        session_service=session_service,
        chat_service=chat_service,
    )
