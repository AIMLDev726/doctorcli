from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from platformdirs import PlatformDirs

from doctorcli.constants import APP_NAME
from doctorcli.exceptions import StorageError


class AppFilesystem:
    def __init__(self) -> None:
        self._dirs = PlatformDirs(appname=APP_NAME, appauthor=False)

    @property
    def config_dir(self) -> Path:
        return Path(self._dirs.user_config_dir)

    @property
    def data_dir(self) -> Path:
        return Path(self._dirs.user_data_dir)

    @property
    def cache_dir(self) -> Path:
        return Path(self._dirs.user_cache_dir)

    @property
    def settings_path(self) -> Path:
        return self.config_dir / "settings.json"

    @property
    def sessions_dir(self) -> Path:
        return self.data_dir / "sessions"

    def ensure_layout(self) -> None:
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def read_json(self, path: Path, default: Any) -> Any:
        if not path.exists():
            return default
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise StorageError(f"Unable to read JSON from {path}") from exc

    def write_json(self, path: Path, payload: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=path.parent,
                delete=False,
            ) as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
                handle.flush()
                temp_name = handle.name
            Path(temp_name).replace(path)
        except OSError as exc:
            raise StorageError(f"Unable to write JSON to {path}") from exc
