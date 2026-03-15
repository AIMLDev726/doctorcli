from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ScopeDecision:
    allowed: bool
    response: str | None = None


class ScopeGuardService:
    def assess(self, user_input: str) -> ScopeDecision:
        return ScopeDecision(True)
