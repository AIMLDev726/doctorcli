from __future__ import annotations

from collections.abc import Sequence
from typing import TypeVar

from rich import box
from rich.console import Console, Group
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.text import Text

T = TypeVar("T")


def prompt_non_empty(console: Console, label: str, default: str | None = None) -> str:
    while True:
        if default:
            value = Prompt.ask(f"[accent]{label}[/]", default=default).strip()
        else:
            value = Prompt.ask(f"[accent]{label}[/]").strip()
        if value:
            return value
        console.print("Value is required.", style="error")


def prompt_optional(
    console: Console,
    label: str,
    default: str | None = None,
    password: bool = False,
) -> str | None:
    if password:
        value = Prompt.ask(f"[accent]{label}[/]", password=True).strip()
    elif default:
        value = Prompt.ask(f"[accent]{label}[/]", default=default).strip()
    else:
        value = Prompt.ask(f"[accent]{label}[/]").strip()
    return value or None


def _hint_line(console: Console, hint: str) -> None:
    table = Table.grid(expand=True)
    table.add_column(justify="right")
    table.add_row(f"[grey70]{hint}[/]")
    console.print(table)


def choose_from_menu(console: Console, title: str, options: Sequence[str]) -> int:
    body = Text()
    for index, option in enumerate(options, start=1):
        body.append(f" {index}. ", style="bold #ffd166")
        body.append(option, style="#f6f1ff")
        if index != len(options):
            body.append("\n")
    console.print(
        Panel(
            body,
            title=title,
            border_style="#ff9f1c",
            box=box.ROUNDED,
            style="on #16051d",
        )
    )
    _hint_line(console, "Enter a number")

    while True:
        raw = Prompt.ask("[brand]>[/] select option").strip()
        if raw.isdigit():
            selected = int(raw)
            if 1 <= selected <= len(options):
                return selected - 1
        console.print("Enter a valid option number.", style="error")


def choose_object(
    console: Console,
    title: str,
    columns: list[str],
    rows: list[tuple[T, list[str]]],
) -> T:
    table = Table(box=box.SIMPLE_HEAVY, header_style="bold #ffcf56", expand=True)
    table.add_column("#", style="bold #ffd166", width=4)
    for column in columns:
        table.add_column(column, style="#f6f1ff")
    for index, (_, values) in enumerate(rows, start=1):
        table.add_row(str(index), *values)
    console.print(
        Panel(
            Group(table),
            title=title,
            border_style="#ff6b6b",
            box=box.ROUNDED,
            style="on #14041a",
        )
    )
    _hint_line(console, "Enter a number")

    while True:
        raw = Prompt.ask("[brand]>[/] select item").strip()
        if raw.isdigit():
            selected = int(raw)
            if 1 <= selected <= len(rows):
                return rows[selected - 1][0]
        console.print("Enter a valid item number.", style="error")


def choose_many_objects(
    console: Console,
    title: str,
    columns: list[str],
    rows: list[tuple[T, list[str]]],
) -> list[T]:
    table = Table(box=box.SIMPLE_HEAVY, header_style="bold #ffcf56", expand=True)
    table.add_column("#", style="bold #ffd166", width=4)
    for column in columns:
        table.add_column(column, style="#f6f1ff")
    for index, (_, values) in enumerate(rows, start=1):
        table.add_row(str(index), *values)
    console.print(
        Panel(
            Group(table),
            title=title,
            border_style="#7bdff2",
            box=box.ROUNDED,
            style="on #14041a",
        )
    )
    _hint_line(console, "Comma-separated numbers, or press Enter for none")

    while True:
        raw = Prompt.ask("[brand]>[/] select items").strip()
        if not raw:
            return []

        parts = [part.strip() for part in raw.split(",") if part.strip()]
        if parts and all(part.isdigit() for part in parts):
            indexes: list[int] = []
            valid = True
            for part in parts:
                index = int(part)
                if not 1 <= index <= len(rows):
                    valid = False
                    break
                if index not in indexes:
                    indexes.append(index)
            if valid:
                return [rows[index - 1][0] for index in indexes]

        console.print("Enter comma-separated item numbers or press Enter for none.", style="error")


def confirm(console: Console, label: str, default: bool = False) -> bool:
    return Confirm.ask(f"[accent]{label}[/]", default=default)
