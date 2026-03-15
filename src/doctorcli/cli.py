from __future__ import annotations

import typer

from doctorcli.agents import AGENTS, get_agent
from doctorcli.application import DoctorCliApplication, run_interactive

app = typer.Typer(add_completion=False, no_args_is_help=False)


@app.callback(invoke_without_command=True)
def main_callback(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        run_interactive()


@app.command("agents")
def list_agents() -> None:
    application = DoctorCliApplication()
    for agent in AGENTS:
        application.console.print(f"- {agent.name}: {agent.specialty}")


@app.command("sessions")
def list_sessions() -> None:
    application = DoctorCliApplication()
    previews = application.session_service.list_sessions()
    if not previews:
        application.console.print("No sessions found.")
        return
    for preview in previews:
        agent = get_agent(preview.agent_id)
        application.console.print(
            f"- {preview.name} | {agent.name} | {preview.provider.value} | {preview.model}"
        )


@app.command("settings")
def open_settings() -> None:
    application = DoctorCliApplication()
    application.settings_menu()


def main() -> None:
    app()
