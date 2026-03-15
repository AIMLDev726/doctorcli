from __future__ import annotations

from rich.console import Console
from rich.theme import Theme


def build_console() -> Console:
    theme = Theme(
        {
            "info": "bold #7bdff2",
            "warn": "bold #ffb703",
            "error": "bold #ff4d6d",
            "success": "bold #80ed99",
            "muted": "#b8b8c9",
            "accent": "bold #ffd166",
            "brand": "bold #ff9f1c",
            "brand2": "bold #ff6b6b",
            "panel": "#f5f7ff on #18061f",
            "title": "bold #fff7e6 on #4b1338",
        }
    )
    return Console(theme=theme, highlight=False, soft_wrap=False)
