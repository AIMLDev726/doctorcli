from __future__ import annotations

from doctorcli.constants import DEFAULT_CONTEXT_MESSAGE_LIMIT
from doctorcli.domain.models import AgentProfile, ChatRequest, ChatSession


class MemoryService:
    def __init__(self, max_messages: int = DEFAULT_CONTEXT_MESSAGE_LIMIT) -> None:
        self.max_messages = max_messages

    def build_request(self, session: ChatSession, agent: AgentProfile) -> ChatRequest:
        messages = session.messages[-self.max_messages :]
        return ChatRequest(
            model=session.metadata.model,
            system_prompt=agent.system_prompt,
            messages=messages,
        )

    def describe(self, session: ChatSession) -> str:
        if not session.messages:
            return "No messages yet."
        recent = session.messages[-min(6, len(session.messages)) :]
        return "\n".join(
            f"- {message.role.value}: {message.content[:120]}" for message in recent
        )
