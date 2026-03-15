from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import SecretStr
from rich import box
from rich.align import Align
from rich.columns import Columns
from rich.console import Group
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from doctorcli.agents import AGENTS, get_agent
from doctorcli.constants import WELCOME_COPY
from doctorcli.domain.models import AppSettings, ChatSession, ModelInfo, ProviderSettings, ProviderType, StreamEventType, ToolSettings, ToolType, ToolSource
from doctorcli.exceptions import ConfigurationError, DoctorCliError, ProviderError
from doctorcli.provider_profiles import PROVIDER_PROFILES, get_provider_profile
from doctorcli.tool_profiles import TOOL_PROFILES, get_tool_profile
from doctorcli.providers.registry import ProviderRegistry
from doctorcli.runtime import build_runtime
from doctorcli.ui.menus import choose_from_menu, choose_many_objects, choose_object, confirm, prompt_non_empty, prompt_optional

BANNER_LINES = [
    "██████╗  ██████╗  ██████╗████████╗ ██████╗ ██████╗      ██████╗██╗     ██╗",
    "██╔══██╗██╔═══██╗██╔════╝╚══██╔══╝██╔═══██╗██╔══██╗    ██╔════╝██║     ██║",
    "██║  ██║██║   ██║██║        ██║   ██║   ██║██████╔╝    ██║     ██║     ██║",
    "██║  ██║██║   ██║██║        ██║   ██║   ██║██╔══██╗    ██║     ██║     ██║",
    "██████╔╝╚██████╔╝╚██████╗   ██║   ╚██████╔╝██║  ██║    ╚██████╗███████╗██║",
    "╚═════╝  ╚═════╝  ╚═════╝   ╚═╝    ╚═════╝ ╚═╝  ╚═╝     ╚═════╝╚══════╝╚═╝",
]
BANNER_COLORS = ["#ffd166", "#ffbe0b", "#ff9f1c", "#ff7b54", "#ff5d8f", "#c77dff"]


class DoctorCliApplication:
    def __init__(self) -> None:
        runtime = build_runtime()
        self.console = runtime.console
        self.filesystem = runtime.filesystem
        self.settings_store = runtime.settings_store
        self.session_store = runtime.session_store
        self.provider_registry = runtime.provider_registry
        self.tool_registry = runtime.tool_registry
        self.memory_service = runtime.memory_service
        self.scope_guard = runtime.scope_guard
        self.session_service = runtime.session_service
        self.chat_service = runtime.chat_service

    def run(self) -> None:
        self.filesystem.ensure_layout()
        while True:
            self.console.clear()
            self.console.print(self._render_welcome_screen())
            selection = choose_from_menu(self.console, "Launch", ["Dashboard", "Settings", "Exit"])
            if selection == 0:
                self.dashboard_menu()
            elif selection == 1:
                self.settings_menu()
            else:
                return

    def dashboard_menu(self) -> None:
        while True:
            self.console.clear()
            self.console.print(self._render_dashboard_screen())
            selection = choose_from_menu(
                self.console,
                "Dashboard",
                ["Choose specialist agent", "Continue existing session", "Delete session", "Back"],
            )
            if selection == 0:
                session = self.agent_session_flow()
                if session is not None:
                    self.chat_loop(session)
            elif selection == 1:
                session = self.resume_session_flow()
                if session is not None:
                    self.chat_loop(session)
            elif selection == 2:
                self.delete_session_flow()
            else:
                return

    def agent_session_flow(self) -> ChatSession | None:
        self.console.clear()
        self.console.print(self._render_agent_gallery())
        agent = choose_object(
            self.console,
            "Choose specialist agent",
            ["Agent", "Specialty", "Communication"],
            [(agent, [agent.name, agent.specialty, agent.communication_style]) for agent in AGENTS],
        )
        selection = choose_from_menu(
            self.console,
            f"Agent: {agent.name}",
            ["Start new session", "Open existing session for this agent", "Delete existing session for this agent", "Back"],
        )
        if selection == 0:
            return self.create_session_flow(agent.id)
        if selection == 1:
            return self.resume_session_flow(agent.id)
        if selection == 2:
            self.delete_session_flow(agent.id)
        return None

    def settings_menu(self) -> None:
        while True:
            self.console.clear()
            settings = self.settings_store.load()
            self.console.print(self._render_settings_screen(settings))
            options = [f"Manage {profile.label}" for profile in PROVIDER_PROFILES] + ["Manage Tools", "Back"]
            selection = choose_from_menu(self.console, "Settings", options)
            if selection < len(PROVIDER_PROFILES):
                self.manage_provider(PROVIDER_PROFILES[selection].type)
            elif selection == len(PROVIDER_PROFILES):
                self.manage_tools_menu()
            else:
                return

    def manage_tools_menu(self) -> None:
        while True:
            self.console.clear()
            settings = self.settings_store.load()
            self.console.print(self._render_tool_settings_screen(settings))
            options = [f"Manage {profile.label}" for profile in TOOL_PROFILES] + ["Back"]
            selection = choose_from_menu(self.console, "Tools", options)
            if selection == len(TOOL_PROFILES):
                return
            self.manage_tool(TOOL_PROFILES[selection].type)

    def manage_tool(self, tool_type: ToolType) -> None:
        profile = get_tool_profile(tool_type)
        while True:
            self.console.clear()
            settings = self.settings_store.load()
            tool_settings = settings.tools[tool_type]
            self.console.print(self._render_tool_detail_screen(profile, tool_settings))
            options = [
                "Enable tool" if not tool_settings.enabled else "Disable tool",
                "Update API key" if profile.api_key_required else "Update API key (optional)",
                "Clear API key",
                "Back",
            ]
            selection = choose_from_menu(self.console, f"Manage {profile.label}", options)
            if selection == 0:
                tool_settings.enabled = not tool_settings.enabled
                self.settings_store.update_tool(tool_type, tool_settings)
            elif selection == 1:
                api_key = prompt_optional(self.console, f"{profile.label} API key", password=True)
                if api_key:
                    tool_settings.api_key = SecretStr(api_key)
                    self.settings_store.update_tool(tool_type, tool_settings)
            elif selection == 2:
                tool_settings.api_key = None
                self.settings_store.update_tool(tool_type, tool_settings)
            else:
                return

    def manage_provider(self, provider: ProviderType) -> None:
        profile = get_provider_profile(provider)
        while True:
            self.console.clear()
            settings = self.settings_store.load()
            provider_settings = settings.providers[provider]
            self.console.print(self._render_provider_detail_screen(profile, provider_settings))
            key_label = "Update API key" if profile.api_key_required else "Update API key (optional)"
            selection = choose_from_menu(
                self.console,
                f"Manage {profile.label}",
                [key_label, "Clear API key", "Set base URL override", "Fetch and choose default model", "Back"],
            )
            if selection == 0:
                api_key = prompt_optional(self.console, f"{profile.label} API key", password=True)
                if api_key:
                    provider_settings.api_key = SecretStr(api_key)
                    self.settings_store.update_provider(provider, provider_settings)
            elif selection == 1:
                provider_settings.api_key = None
                self.settings_store.update_provider(provider, provider_settings)
            elif selection == 2:
                base_url = prompt_optional(self.console, "Base URL override", default=provider_settings.base_url or profile.base_url_hint)
                provider_settings.base_url = base_url
                self.settings_store.update_provider(provider, provider_settings)
            elif selection == 3:
                self.fetch_and_choose_default_model(provider)
            else:
                return

    def create_session_flow(self, agent_id: str) -> ChatSession | None:
        self.console.clear()
        agent = get_agent(agent_id)
        self.console.print(self._render_session_create_screen(agent.id))
        name = prompt_non_empty(self.console, "Session name")
        reason = prompt_non_empty(self.console, "Reason for consultation")
        provider = choose_object(
            self.console,
            "Choose provider",
            ["Provider", "Type", "Base URL"],
            [
                (profile.type, [profile.label, "Local" if profile.local_first else "Cloud", profile.base_url_hint])
                for profile in PROVIDER_PROFILES
            ],
        )
        model = self.choose_model_for_provider(provider)
        if model is None:
            return None
        tools = self.choose_tools_for_session()
        return self.session_service.create_session(
            name=name,
            reason=reason,
            agent_id=agent.id,
            provider=provider,
            model=model.id,
            tools=tools,
        )

    def choose_tools_for_session(self) -> list[ToolType]:
        settings = self.settings_store.load()
        rows: list[tuple[ToolType, list[str]]] = []
        for profile in TOOL_PROFILES:
            tool_settings = settings.tools[profile.type]
            status = "Enabled" if tool_settings.enabled else "Disabled"
            if profile.api_key_required and tool_settings.api_key is None:
                status = f"{status} | key needed"
            rows.append((profile.type, [profile.label, profile.category, status, profile.setup_hint]))

        selected = choose_many_objects(
            self.console,
            "Optional tools for this session",
            ["Tool", "Category", "Status", "Setup"],
            rows,
        )
        if not selected:
            return []

        refreshed = self.settings_store.load()
        attached: list[ToolType] = []
        for tool_type in selected:
            tool_settings = refreshed.tools[tool_type]
            profile = get_tool_profile(tool_type)
            if not tool_settings.enabled:
                self.console.print(
                    Panel.fit(
                        f"{profile.label} is disabled in settings and was skipped.",
                        title="Tool skipped",
                        border_style="#ffb703",
                        style="on #18061f",
                        box=box.ROUNDED,
                    )
                )
                continue
            if profile.api_key_required and tool_settings.api_key is None:
                self.console.print(
                    Panel.fit(
                        f"{profile.label} needs an API key for this session. Enter it now to attach the tool, or leave it blank to skip.",
                        title="Tool setup",
                        border_style="#ffb703",
                        style="on #18061f",
                        box=box.ROUNDED,
                    )
                )
                api_key = prompt_optional(self.console, f"{profile.label} API key", password=True)
                if not api_key:
                    self.console.print(
                        Panel.fit(
                            f"{profile.label} was not configured and will not be attached to this session.",
                            title="Tool skipped",
                            border_style="#ffb703",
                            style="on #18061f",
                            box=box.ROUNDED,
                        )
                    )
                    continue
                tool_settings.api_key = SecretStr(api_key)
                self.settings_store.update_tool(tool_type, tool_settings)
            attached.append(tool_type)
        return attached

    def resume_session_flow(self, agent_id: str | None = None) -> ChatSession | None:
        previews = self.session_service.list_sessions()
        if agent_id is not None:
            previews = [preview for preview in previews if preview.agent_id == agent_id]
        if not previews:
            self.console.print(Panel.fit("No sessions found.", title="Sessions", border_style="#ffb703", style="on #18061f", box=box.ROUNDED))
            self.console.input("Press Enter to continue...")
            return None
        selected = choose_object(
            self.console,
            "Choose session",
            ["Name", "Agent", "Provider", "Model", "Updated", "Messages"],
            [
                (
                    preview,
                    [
                        preview.name,
                        get_agent(preview.agent_id).name,
                        get_provider_profile(preview.provider).label,
                        preview.model,
                        self._format_dt(preview.updated_at),
                        str(preview.message_count),
                    ],
                )
                for preview in previews
            ],
        )
        return self.session_service.load(selected.id)

    def delete_session_flow(self, agent_id: str | None = None) -> None:
        previews = self.session_service.list_sessions()
        if agent_id is not None:
            previews = [preview for preview in previews if preview.agent_id == agent_id]
        if not previews:
            self.console.print(Panel.fit("No sessions available to delete.", title="Delete Session", border_style="#ffb703", style="on #18061f", box=box.ROUNDED))
            self.console.input("Press Enter to continue...")
            return
        selected = choose_object(
            self.console,
            "Delete session",
            ["Name", "Agent", "Provider", "Updated"],
            [
                (
                    preview,
                    [
                        preview.name,
                        get_agent(preview.agent_id).name,
                        get_provider_profile(preview.provider).label,
                        self._format_dt(preview.updated_at),
                    ],
                )
                for preview in previews
            ],
        )
        if confirm(self.console, f"Delete session '{selected.name}'?", default=False):
            self.session_service.delete(selected.id)
            self.console.print("Session deleted.", style="success")
            self.console.input("Press Enter to continue...")

    def choose_model_for_provider(self, provider: ProviderType) -> ModelInfo | None:
        profile = get_provider_profile(provider)
        settings = self.settings_store.load()
        provider_settings = settings.providers[provider]
        if profile.api_key_required and provider_settings.api_key is None:
            api_key = prompt_optional(self.console, f"{profile.label} API key", password=True)
            if not api_key:
                self.console.print("API key is required to continue.", style="error")
                self.console.input("Press Enter to continue...")
                return None
            provider_settings.api_key = SecretStr(api_key)
            self.settings_store.update_provider(provider, provider_settings)
            provider_settings = self.settings_store.load().providers[provider]

        try:
            models = self.fetch_models(provider, provider_settings)
        except DoctorCliError as exc:
            self.console.print(Panel.fit(str(exc), title="Model fetch failed", border_style="#ff4d6d", style="on #18061f", box=box.ROUNDED))
            self.console.input("Press Enter to continue...")
            return None
        if not models:
            self.console.print(Panel.fit("No models available for this provider.", title="Model fetch", border_style="#ff4d6d", style="on #18061f", box=box.ROUNDED))
            self.console.input("Press Enter to continue...")
            return None

        default_model = provider_settings.default_model
        if default_model:
            matching_default = next((item for item in models if item.id == default_model), None)
            if matching_default and confirm(self.console, f"Use default model '{default_model}'?", default=True):
                return matching_default

        return choose_object(
            self.console,
            f"Choose model for {profile.label}",
            ["Model", "Thinking", "Created", "Description"],
            [
                (
                    model,
                    [
                        model.id,
                        "Yes" if model.thinking_supported else "No",
                        self._format_dt(model.created),
                        (model.description or "")[:70],
                    ],
                )
                for model in models
            ],
        )

    def fetch_models(self, provider: ProviderType, provider_settings: ProviderSettings) -> list[ModelInfo]:
        client = self.provider_registry.get(provider)
        try:
            models = client.list_models(provider_settings)
            self.settings_store.update_model_cache(provider, models)
            return models
        except DoctorCliError as exc:
            if provider_settings.model_cache:
                self.console.print(
                    Panel.fit(
                        f"Live model fetch failed. Using cached models.\n\n{exc}",
                        title="Provider warning",
                        border_style="#ffb703",
                        style="on #18061f",
                        box=box.ROUNDED,
                    )
                )
                return provider_settings.model_cache
            raise

    def fetch_and_choose_default_model(self, provider: ProviderType) -> None:
        profile = get_provider_profile(provider)
        settings = self.settings_store.load()
        provider_settings = settings.providers[provider]
        if profile.api_key_required and provider_settings.api_key is None:
            self.console.print(Panel.fit("Configure the API key first.", title="Provider settings", border_style="#ff4d6d", style="on #18061f", box=box.ROUNDED))
            self.console.input("Press Enter to continue...")
            return
        try:
            models = self.fetch_models(provider, provider_settings)
        except DoctorCliError as exc:
            self.console.print(Panel.fit(str(exc), title="Model fetch failed", border_style="#ff4d6d", style="on #18061f", box=box.ROUNDED))
            self.console.input("Press Enter to continue...")
            return
        selected = choose_object(
            self.console,
            f"Choose default model for {profile.label}",
            ["Model", "Thinking", "Created"],
            [
                (model, [model.id, "Yes" if model.thinking_supported else "No", self._format_dt(model.created)])
                for model in models
            ],
        )
        provider_settings.default_model = selected.id
        self.settings_store.update_provider(provider, provider_settings)

    def chat_loop(self, session: ChatSession) -> None:
        self._show_chat_shell(session)
        while True:
            settings = self.settings_store.load()
            provider_settings = settings.providers[session.metadata.provider]
            user_input = self.console.input("[bold #ffd166]>[/] ").strip()
            if not user_input:
                continue
            if user_input == "/exit":
                return
            if user_input == "/memory":
                self.console.print(Panel.fit(self.memory_service.describe(session), title="Session Memory", border_style="#ffb703", style="on #18061f", box=box.ROUNDED))
                continue
            if user_input == "/settings":
                self.settings_menu()
                self._show_chat_shell(session)
                continue
            if user_input == "/session":
                settings = self.settings_store.load()
                provider_settings = settings.providers[session.metadata.provider]
                self.console.print(self._render_session_header(session, provider_settings))
                continue

            decision = self.scope_guard.assess(user_input)
            if not decision.allowed:
                self.session_service.add_user_message(session, user_input)
                local_response = decision.response or ""
                self.session_service.add_assistant_message(session, local_response)
                self._stream_local_response(local_response, border_style="#ffb703")
                self.console.print()
                continue

            if get_provider_profile(session.metadata.provider).api_key_required and provider_settings.api_key is None:
                api_key = prompt_optional(self.console, f"{get_provider_profile(session.metadata.provider).label} API key", password=True)
                if not api_key:
                    self.console.print("API key is required.", style="error")
                    continue
                provider_settings.api_key = SecretStr(api_key)
                self.settings_store.update_provider(session.metadata.provider, provider_settings)
                provider_settings = self.settings_store.load().providers[session.metadata.provider]

            try:
                self._stream_assistant_response(session, provider_settings, user_input)
                self.console.print()
            except (ConfigurationError, ProviderError) as exc:
                self.console.print(Panel.fit(str(exc), title="Request failed", border_style="#ff4d6d", style="on #18061f", box=box.ROUNDED))

    def _show_chat_shell(self, session: ChatSession) -> None:
        self.console.clear()
        settings = self.settings_store.load()
        provider_settings = settings.providers[session.metadata.provider]
        self.console.print(self._render_chat_intro(session, provider_settings))
        if session.messages:
            self.console.print(self._render_recent_history(session))
        self.console.print(self._render_prompt_bar())

    def _stream_assistant_response(self, session: ChatSession, provider_settings: ProviderSettings, user_input: str) -> None:
        content_buffer = ""
        reasoning_buffer = ""
        tool_events: list[dict[str, Any]] = []
        stream = self.chat_service.stream_turn(session, provider_settings, user_input)

        with Live(self._render_stream(reasoning_buffer, content_buffer, tool_events), console=self.console, refresh_per_second=10) as live:
            for event in stream:
                if event.type == StreamEventType.REASONING:
                    reasoning_buffer += event.text
                elif event.type == StreamEventType.CONTENT:
                    content_buffer += event.text
                elif event.type == StreamEventType.TOOL:
                    tool_events.append(event.raw)
                live.update(self._render_stream(reasoning_buffer, content_buffer, tool_events))

    def _stream_local_response(self, content: str, border_style: str = "#7bdff2") -> None:
        words = content.split()
        if not words:
            self.console.print(self._render_local_stream_panel("", border_style))
            return

        rendered = ""
        with Live(self._render_local_stream_panel(rendered, border_style), console=self.console, refresh_per_second=18) as live:
            for word in words:
                rendered = f"{rendered} {word}".strip()
                live.update(self._render_local_stream_panel(rendered, border_style))

    def _render_local_stream_panel(self, content: str, border_style: str):
        return Panel(
            Text(content or "Preparing local response...", style="#f5f7ff"),
            title="Assistant",
            border_style=border_style,
            box=box.HEAVY,
            style="on #120318",
        )

    def _render_stream(self, reasoning: str, content: str, tool_events: list[dict[str, Any]] | None = None):
        parts: list[Any] = []
        if reasoning.strip():
            parts.append(
                Panel(
                    Markdown(reasoning),
                    title="Thinking",
                    border_style="#ffd166",
                    box=box.HEAVY,
                    style="on #16051d",
                )
            )
        for tool_event in tool_events or []:
            parts.append(self._render_tool_event_panel(tool_event))
        parts.append(
            Panel(
                Markdown(content or "_Waiting for model output..._"),
                title="Assistant",
                border_style="#7bdff2",
                box=box.HEAVY,
                style="on #120318",
            )
        )
        return Group(*parts)

    def _render_tool_event_panel(self, tool_event: dict[str, Any]):
        body_items: list[Any] = []
        tool_name = str(tool_event.get("name", "tool"))
        query = str(tool_event.get("query", "")).strip()
        summary = str(tool_event.get("content", "")).strip()
        if query:
            body_items.append(Text(f"Query: {query}", style="#ffd166"))
            body_items.append(Rule(style="#2c1a39"))
        if summary:
            preview = summary if len(summary) <= 400 else f"{summary[:397]}..."
            body_items.append(Text(preview, style="#f6f1ff"))
        sources = [ToolSource.model_validate(item) for item in tool_event.get("sources", [])]
        if sources:
            if body_items:
                body_items.append(Rule(style="#2c1a39"))
            table = Table(box=box.MINIMAL, expand=True)
            table.add_column("Source", style="#ffd166")
            table.add_column("Link", style="#7bdff2")
            table.add_column("Snippet", style="#cbd5ff")
            for source in sources:
                table.add_row(
                    source.title,
                    source.url or "-",
                    (source.snippet or "-")[:120],
                )
            body_items.append(table)
        if not body_items:
            body_items.append(Text("Tool executed.", style="#f6f1ff"))
        return Panel(
            Group(*body_items),
            title=f"Tool Call: {tool_name}",
            border_style="#ffb703",
            box=box.ROUNDED,
            style="on #14041a",
        )

    def _render_welcome_screen(self):
        tips = Table.grid(padding=(0, 1))
        tips.add_column(style="#f5f7ff")
        tips.add_row("[bold #ffd166]Tips for getting started[/]")
        tips.add_row("1. Choose a specialist instead of using a generic agent.")
        tips.add_row("2. Keep the consultation reason specific.")
        tips.add_row("3. Configure providers and tools in Settings.")
        tips.add_row("4. Use saved sessions to maintain continuity.")
        return Group(
            self._hero_panel("clinical specialist shell"),
            Panel(tips, border_style="#7b2cbf", style="on #19061f", box=box.SQUARE),
            self._render_input_preview("Type symptoms, medications, labs, or follow-up questions"),
            self._status_strip([
                ("workspace", "doctorcli"),
                ("providers", str(len(PROVIDER_PROFILES))),
                ("sessions", str(len(self.session_service.list_sessions()))),
            ]),
        )

    def _render_dashboard_screen(self):
        settings = self.settings_store.load()
        sessions = self.session_service.list_sessions()
        ready = sum(1 for profile in PROVIDER_PROFILES if settings.providers[profile.type].api_key is not None or not profile.api_key_required)
        enabled_tools = sum(1 for profile in TOOL_PROFILES if settings.tools[profile.type].enabled)
        cards = Columns(
            [
                self._metric_panel("Session Vault", str(len(sessions)), "saved case histories", "#7bdff2"),
                self._metric_panel("Provider Grid", f"{ready}/{len(PROVIDER_PROFILES)}", "configured runtimes", "#80ed99"),
                self._metric_panel("Tool Rack", f"{enabled_tools}/{len(TOOL_PROFILES)}", "session tools available", "#ffb703"),
            ],
            equal=True,
            expand=True,
        )
        latest = Table(box=box.MINIMAL_HEAVY_HEAD, header_style="bold #ffd166", expand=True)
        latest.add_column("Session", style="#f6f1ff")
        latest.add_column("Agent", style="#f6f1ff")
        latest.add_column("Provider", style="#f6f1ff")
        latest.add_column("Updated", style="#c7d3ff")
        for preview in sessions[:6]:
            latest.add_row(preview.name, get_agent(preview.agent_id).name, get_provider_profile(preview.provider).label, self._format_dt(preview.updated_at))
        if not sessions:
            latest.add_row("No sessions yet", "-", "-", "-")
        return Group(
            self._section_panel("dashboard", "sessions, providers, and configured tools"),
            cards,
            Panel(latest, title="Recent sessions", border_style="#ff6b6b", style="on #130319", box=box.ROUNDED),
            self._status_strip([
                ("continue", "resume previous work"),
                ("delete", "remove stale sessions"),
                ("agent", "start a new specialist flow"),
            ]),
        )

    def _render_agent_gallery(self):
        cards = [
            Panel(
                f"[bold #ffd166]{agent.specialty}[/]\n\n{agent.summary}\n\n[grey70]{agent.communication_style}[/]",
                title=agent.name,
                border_style="#7bdff2",
                style="on #14041a",
                box=box.ROUNDED,
            )
            for agent in AGENTS
        ]
        return Group(self._section_panel("specialist matrix", "choose the most relevant clinical persona"), Columns(cards, equal=True, expand=True))

    def _render_settings_screen(self, settings: AppSettings):
        provider_cards = []
        for profile in PROVIDER_PROFILES:
            provider_settings = settings.providers[profile.type]
            accent = "#80ed99" if provider_settings.api_key or not profile.api_key_required else "#ffb703"
            provider_cards.append(
                Panel(
                    Group(
                        Text(profile.description, style="#e9ebff"),
                        Rule(style="#2b1937"),
                        Text(f"API key   {provider_settings.masked_api_key()}", style="#f6f1ff"),
                        Text(f"Model     {provider_settings.default_model or '-'}", style="#f6f1ff"),
                        Text(f"Cache     {len(provider_settings.model_cache)} models", style="#c7d3ff"),
                        Text(f"Base URL  {provider_settings.base_url or profile.base_url_hint}", style="#c7d3ff"),
                    ),
                    title=profile.label,
                    border_style=accent,
                    style="on #14041a",
                    box=box.ROUNDED,
                )
            )
        tool_cards = []
        for profile in TOOL_PROFILES:
            tool_settings = settings.tools[profile.type]
            accent = "#80ed99" if tool_settings.enabled and (tool_settings.api_key is not None or not profile.api_key_required) else "#ffb703"
            tool_cards.append(
                Panel(
                    Group(
                        Text(profile.description, style="#e9ebff"),
                        Rule(style="#2b1937"),
                        Text(f"Status    {'Enabled' if tool_settings.enabled else 'Disabled'}", style="#f6f1ff"),
                        Text(f"API key   {tool_settings.masked_api_key()}", style="#f6f1ff"),
                        Text(f"Setup     {profile.setup_hint}", style="#c7d3ff"),
                    ),
                    title=profile.label,
                    border_style=accent,
                    style="on #14041a",
                    box=box.ROUNDED,
                )
            )
        return Group(
            self._section_panel("settings", "providers and optional tools"),
            Panel(Columns(provider_cards, equal=True, expand=True), title="Providers", border_style="#7bdff2", style="on #120318", box=box.ROUNDED),
            Panel(Columns(tool_cards, equal=True, expand=True), title="Tools", border_style="#ffb703", style="on #120318", box=box.ROUNDED),
        )

    def _render_provider_detail_screen(self, profile, settings: ProviderSettings):
        left = Panel(
            Group(
                Text(profile.description, style="#f1f4ff"),
                Rule(style="#2c1a39"),
                Text(f"API key      {settings.masked_api_key()}", style="#ffd166"),
                Text(f"Base URL     {settings.base_url or profile.base_url_hint}", style="#f1f4ff"),
                Text(f"Default      {settings.default_model or '-'}", style="#f1f4ff"),
                Text(f"Cache size   {len(settings.model_cache)} models", style="#cbd5ff"),
                Text(f"Last sync    {self._format_dt(settings.model_cache_updated_at)}", style="#cbd5ff"),
            ),
            title=f"{profile.label} profile",
            border_style="#7bdff2",
            style="on #14041a",
            box=box.DOUBLE,
        )
        right = Panel(
            Group(
                Text("Controls", style="bold #ffd166"),
                Text("- update key", style="#f5f7ff"),
                Text("- clear key", style="#f5f7ff"),
                Text("- override base url", style="#f5f7ff"),
                Text("- fetch latest model catalog", style="#f5f7ff"),
                Rule(style="#2c1a39"),
                Text("Cloud providers require valid keys.", style="#cbd5ff") if profile.api_key_required else Text("Local providers can run without a key.", style="#cbd5ff"),
            ),
            title="Ops",
            border_style="#ff6b6b",
            style="on #120318",
            box=box.ROUNDED,
        )
        return Group(self._section_panel(profile.label.lower(), profile.description), Columns([left, right], equal=True, expand=True))

    def _render_tool_settings_screen(self, settings: AppSettings):
        cards = []
        for profile in TOOL_PROFILES:
            tool_settings = settings.tools[profile.type]
            accent = "#80ed99" if tool_settings.enabled and (tool_settings.api_key is not None or not profile.api_key_required) else "#ffb703"
            cards.append(
                Panel(
                    Group(
                        Text(profile.description, style="#f1f4ff"),
                        Rule(style="#2c1a39"),
                        Text(f"Category    {profile.category}", style="#f1f4ff"),
                        Text(f"Status      {'Enabled' if tool_settings.enabled else 'Disabled'}", style="#ffd166"),
                        Text(f"API key     {tool_settings.masked_api_key()}", style="#f1f4ff"),
                        Text(f"Setup       {profile.setup_hint}", style="#cbd5ff"),
                    ),
                    title=profile.label,
                    border_style=accent,
                    style="on #14041a",
                    box=box.ROUNDED,
                )
            )
        return Group(self._section_panel("tools", "configure optional session tools"), Columns(cards, equal=True, expand=True))

    def _render_tool_detail_screen(self, profile, settings: ToolSettings):
        return Group(
            self._section_panel(profile.label.lower(), profile.description),
            Panel(
                Group(
                    Text(f"Category    {profile.category}", style="#f1f4ff"),
                    Text(f"Status      {'Enabled' if settings.enabled else 'Disabled'}", style="#ffd166"),
                    Text(f"API key     {settings.masked_api_key()}", style="#f1f4ff"),
                    Text(f"Setup       {profile.setup_hint}", style="#cbd5ff"),
                ),
                title=f"{profile.label} tool",
                border_style="#7bdff2",
                style="on #14041a",
                box=box.DOUBLE,
            ),
        )

    def _render_session_create_screen(self, agent_id: str):
        agent = get_agent(agent_id)
        steps = Table.grid(padding=(0, 1))
        steps.add_column(style="#f6f1ff")
        steps.add_row("01  name the session")
        steps.add_row("02  define the medical reason")
        steps.add_row("03  choose provider and model")
        steps.add_row("04  attach optional tools")
        steps.add_row("05  launch the specialist chat")
        left = Panel(
            Group(
                Text(agent.name, style="bold #ffd166"),
                Text(agent.specialty, style="#7bdff2"),
                Rule(style="#2c1a39"),
                Text(agent.summary, style="#f3f5ff"),
                Text(agent.communication_style, style="#cbd5ff"),
            ),
            title="Selected specialist",
            border_style="#7bdff2",
            style="on #14041a",
            box=box.DOUBLE,
        )
        right = Panel(steps, title="Boot sequence", border_style="#ff6b6b", style="on #120318", box=box.ROUNDED)
        return Group(
            self._section_panel("session onboarding", "configure the session once, then reuse it later"),
            Columns([left, right], equal=True, expand=True),
            self._render_input_preview("Session name, reason, provider, model, then optional tools"),
        )

    def _render_chat_intro(self, session: ChatSession, provider_settings: ProviderSettings):
        left = self._render_session_header(session, provider_settings)
        right = Panel(
            Group(
                Text(f"Agent    {get_agent(session.metadata.agent_id).name}", style="#f6f1ff"),
                Text(f"Provider {get_provider_profile(session.metadata.provider).label}", style="#f6f1ff"),
                Text(f"Model    {session.metadata.model}", style="#ffd166"),
                Text(f"Thinking {self._thinking_note(session.metadata.model, provider_settings)}", style="#cbd5ff"),
                Text(f"Tools    {self._tool_summary(session.metadata.tools)}", style="#cbd5ff"),
            ),
            title="Runtime",
            border_style="#ff6b6b",
            style="on #120318",
            box=box.ROUNDED,
        )
        return Group(self._section_panel("live consultation", session.metadata.name), Columns([left, right], equal=True, expand=True))

    def _render_session_header(self, session: ChatSession, provider_settings: ProviderSettings):
        body = Group(
            Text(f"Session  {session.metadata.name}", style="#ffd166"),
            Text(f"Reason   {session.metadata.reason}", style="#f6f1ff"),
            Text(f"Messages {len(session.messages)}", style="#f6f1ff"),
            Text(f"Tools    {self._tool_summary(session.metadata.tools)}", style="#f6f1ff"),
            Text(f"API Key  {provider_settings.masked_api_key()}", style="#cbd5ff"),
        )
        return Panel(body, title="Active session", border_style="#7bdff2", style="on #14041a", box=box.DOUBLE)

    def _render_recent_history(self, session: ChatSession):
        table = Table(box=box.MINIMAL_HEAVY_HEAD, header_style="bold #ffd166", expand=True)
        table.add_column("Role", style="#ffd166", width=10)
        table.add_column("Transcript", style="#f6f1ff")
        for message in session.messages[-8:]:
            preview = message.content.replace("\n", " ").strip()
            if len(preview) > 160:
                preview = f"{preview[:157]}..."
            table.add_row(message.role.value.upper(), preview)
        return Panel(table, title="Recent transcript", border_style="#7b2cbf", style="on #120318", box=box.ROUNDED)

    def _render_prompt_bar(self):
        return Group(
            self._render_input_preview("Type a health question or command"),
            self._status_strip([
                ("/exit", "leave session"),
                ("/memory", "show session memory"),
                ("/settings", "open full settings"),
                ("/session", "session metadata"),
            ]),
        )

    def _hero_panel(self, subtitle: str):
        return Panel(
            Group(
                Align.center(self._banner_text()),
                Align.center(Text(subtitle.upper(), style="bold #c77dff")),
                Align.center(Text(WELCOME_COPY, style="#cbd5ff")),
            ),
            border_style="#ff9f1c",
            style="on #18061f",
            box=box.DOUBLE_EDGE,
        )

    def _section_panel(self, title: str, subtitle: str):
        return Panel(
            Group(
                Align.center(Text(title.upper(), style="bold #ffd166")),
                Align.center(Text(subtitle, style="#cbd5ff")),
            ),
            border_style="#ff9f1c",
            style="on #18061f",
            box=box.ROUNDED,
        )

    def _banner_text(self) -> Text:
        text = Text()
        for color, line in zip(BANNER_COLORS, BANNER_LINES):
            text.append(line + "\n", style=f"bold {color}")
        return text

    def _render_input_preview(self, placeholder: str):
        return Panel(Text(f"> {placeholder}", style="#d8dcff"), border_style="#7bdff2", box=box.SQUARE, style="on #110216")

    def _status_strip(self, items: list[tuple[str, str]]):
        table = Table.grid(expand=True)
        for _ in items:
            table.add_column(justify="center")
        table.add_row(*[f"[bold #ffd166]{label}[/]\n[grey70]{value}[/]" for label, value in items])
        return Panel(table, border_style="#2c1a39", style="on #110216", box=box.SQUARE)

    def _metric_panel(self, title: str, value: str, subtitle: str, color: str):
        return Panel(
            Group(Align.center(Text(value, style=f"bold {color}")), Align.center(Text(subtitle, style="#cbd5ff"))),
            title=title,
            border_style=color,
            style="on #130319",
            box=box.ROUNDED,
        )

    def _thinking_note(self, model_id: str, provider_settings: ProviderSettings) -> str:
        model = next((item for item in provider_settings.model_cache if item.id == model_id), None)
        if model and model.thinking_supported:
            return "supported and auto-shown"
        return "provider-controlled"

    def _tool_summary(self, tools: list[ToolType]) -> str:
        if not tools:
            return "none"
        return ", ".join(get_tool_profile(tool).label for tool in tools)

    def _format_dt(self, value: datetime | None) -> str:
        if value is None:
            return "-"
        return value.astimezone().strftime("%Y-%m-%d %H:%M")


def run_interactive() -> None:
    app = DoctorCliApplication()
    app.run()






















