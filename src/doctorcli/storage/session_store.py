from __future__ import annotations

from pathlib import Path

from doctorcli.domain.models import ChatSession, SessionPreview
from doctorcli.storage.filesystem import AppFilesystem


class SessionStore:
    def __init__(self, filesystem: AppFilesystem) -> None:
        self.filesystem = filesystem

    def _session_path(self, session_id: str) -> Path:
        return self.filesystem.sessions_dir / f"{session_id}.json"

    def save(self, session: ChatSession) -> None:
        session.touch()
        self.filesystem.ensure_layout()
        self.filesystem.write_json(
            self._session_path(session.metadata.id),
            session.model_dump(mode="json", exclude_none=True),
        )

    def load(self, session_id: str) -> ChatSession:
        payload = self.filesystem.read_json(self._session_path(session_id), default=None)
        if payload is None:
            raise FileNotFoundError(session_id)
        return ChatSession.model_validate(payload)

    def delete(self, session_id: str) -> bool:
        path = self._session_path(session_id)
        if not path.exists():
            return False
        path.unlink()
        return True

    def list_previews(self) -> list[SessionPreview]:
        self.filesystem.ensure_layout()
        previews: list[SessionPreview] = []
        for path in sorted(
            self.filesystem.sessions_dir.glob("*.json"),
            key=lambda entry: entry.stat().st_mtime,
            reverse=True,
        ):
            payload = self.filesystem.read_json(path, default=None)
            if payload is None:
                continue
            session = ChatSession.model_validate(payload)
            previews.append(
                SessionPreview(
                    id=session.metadata.id,
                    name=session.metadata.name,
                    reason=session.metadata.reason,
                    agent_id=session.metadata.agent_id,
                    provider=session.metadata.provider,
                    model=session.metadata.model,
                    created_at=session.metadata.created_at,
                    updated_at=session.metadata.updated_at,
                    message_count=len(session.messages),
                )
            )
        return previews
