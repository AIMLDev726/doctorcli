from __future__ import annotations

from doctorcli.domain.models import ChatSession, MessageRole, ProviderType, SessionMessage, SessionMetadata, SessionPreview, ToolType
from doctorcli.storage.session_store import SessionStore


class SessionService:
    def __init__(self, session_store: SessionStore) -> None:
        self.session_store = session_store

    def create_session(
        self,
        name: str,
        reason: str,
        agent_id: str,
        provider: ProviderType,
        model: str,
        tools: list[ToolType] | None = None,
    ) -> ChatSession:
        session = ChatSession(
            metadata=SessionMetadata(
                name=name,
                reason=reason,
                agent_id=agent_id,
                provider=provider,
                model=model,
                tools=tools or [],
            )
        )
        self.session_store.save(session)
        return session

    def save(self, session: ChatSession) -> None:
        self.session_store.save(session)

    def list_sessions(self) -> list[SessionPreview]:
        return self.session_store.list_previews()

    def load(self, session_id: str) -> ChatSession:
        return self.session_store.load(session_id)

    def delete(self, session_id: str) -> bool:
        return self.session_store.delete(session_id)

    def add_user_message(self, session: ChatSession, content: str) -> SessionMessage:
        message = SessionMessage(role=MessageRole.USER, content=content)
        session.messages.append(message)
        self.session_store.save(session)
        return message

    def add_assistant_message(
        self,
        session: ChatSession,
        content: str,
        reasoning: str | None = None,
    ) -> SessionMessage:
        message = SessionMessage(
            role=MessageRole.ASSISTANT,
            content=content,
            reasoning=reasoning or None,
        )
        session.messages.append(message)
        self.session_store.save(session)
        return message
