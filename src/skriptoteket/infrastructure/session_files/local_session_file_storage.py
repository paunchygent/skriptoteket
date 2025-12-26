from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

from skriptoteket.domain.errors import validation_error
from skriptoteket.domain.scripting.input_files import normalize_input_files
from skriptoteket.domain.scripting.tool_sessions import normalize_tool_session_context
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.session_files import (
    CleanupExpiredSessionFilesResult,
    InputFile,
    SessionFileStorageProtocol,
)

_META_FILENAME = "meta.json"
_RESERVED_FILENAMES = {"action.json"}


@dataclass(frozen=True)
class _SessionKey:
    tool_id: UUID
    user_id: UUID
    context: str
    context_key: str


def _context_key(*, context: str) -> str:
    return hashlib.sha256(context.encode("utf-8")).hexdigest()


def _safe_write_json(*, path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.name}.tmp-{uuid4()}")
    try:
        tmp_path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), "utf-8")
        tmp_path.replace(path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


def _parse_last_accessed_at(*, value: object) -> str | None:
    if not isinstance(value, str) or not value.strip():
        return None
    return value


class LocalSessionFileStorage(SessionFileStorageProtocol):
    """Filesystem-backed session file storage (ADR-0039).

    Layout:
      {sessions_root}/sessions/{tool_id}/{user_id}/{context_key}/
    """

    def __init__(
        self,
        *,
        sessions_root: Path,
        ttl_seconds: int,
        clock: ClockProtocol,
    ) -> None:
        self._sessions_root = sessions_root
        self._ttl_seconds = ttl_seconds
        self._clock = clock

    def _key(self, *, tool_id: UUID, user_id: UUID, context: str) -> _SessionKey:
        normalized_context = normalize_tool_session_context(context=context)
        return _SessionKey(
            tool_id=tool_id,
            user_id=user_id,
            context=normalized_context,
            context_key=_context_key(context=normalized_context),
        )

    def _session_dir(self, key: _SessionKey) -> Path:
        return (
            self._sessions_root / "sessions" / str(key.tool_id) / str(key.user_id) / key.context_key
        )

    def _meta_path(self, session_dir: Path) -> Path:
        return session_dir / _META_FILENAME

    def _build_meta(self, *, key: _SessionKey, now_iso: str) -> dict[str, object]:
        return {
            "context": key.context,
            "context_key": key.context_key,
            "last_accessed_at": now_iso,
        }

    def _read_meta(self, *, session_dir: Path) -> dict[str, object] | None:
        meta_path = self._meta_path(session_dir)
        if not meta_path.exists():
            return None
        try:
            raw = json.loads(meta_path.read_text("utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        return raw if isinstance(raw, dict) else None

    async def store_files(
        self,
        *,
        tool_id: UUID,
        user_id: UUID,
        context: str,
        files: list[InputFile],
    ) -> None:
        if not files:
            raise validation_error("files is required")

        key = self._key(tool_id=tool_id, user_id=user_id, context=context)
        normalized_files = normalize_input_files(input_files=files)[0]
        for name, _content in normalized_files:
            if name in _RESERVED_FILENAMES:
                raise validation_error(
                    "Filename is reserved; rename the file.",
                    details={"filename": name},
                )

        session_dir = self._session_dir(key)
        parent_dir = session_dir.parent
        parent_dir.mkdir(parents=True, exist_ok=True)

        temp_dir = parent_dir / f"{key.context_key}.tmp-{uuid4()}"
        old_dir: Path | None = None

        now_iso = self._clock.now().isoformat()
        temp_dir.mkdir(parents=True, exist_ok=False)
        try:
            for name, content in normalized_files:
                (temp_dir / name).write_bytes(content)

            _safe_write_json(
                path=self._meta_path(temp_dir),
                payload=self._build_meta(key=key, now_iso=now_iso),
            )

            if session_dir.exists():
                old_dir = parent_dir / f"{key.context_key}.old-{uuid4()}"
                session_dir.rename(old_dir)

            temp_dir.rename(session_dir)
        except Exception:
            shutil.rmtree(temp_dir, ignore_errors=True)
            if old_dir is not None and not session_dir.exists():
                try:
                    old_dir.rename(session_dir)
                except OSError:
                    pass
            raise
        finally:
            if old_dir is not None:
                shutil.rmtree(old_dir, ignore_errors=True)

    async def get_files(
        self,
        *,
        tool_id: UUID,
        user_id: UUID,
        context: str,
    ) -> list[InputFile]:
        key = self._key(tool_id=tool_id, user_id=user_id, context=context)
        session_dir = self._session_dir(key)
        if not session_dir.exists():
            return []

        files: list[InputFile] = []
        for item in sorted(session_dir.iterdir(), key=lambda path: path.name):
            if item.name == _META_FILENAME:
                continue
            if not item.is_file():
                continue
            files.append((item.name, item.read_bytes()))

        now_iso = self._clock.now().isoformat()
        _safe_write_json(
            path=self._meta_path(session_dir),
            payload=self._build_meta(key=key, now_iso=now_iso),
        )
        return files

    async def clear_session(
        self,
        *,
        tool_id: UUID,
        user_id: UUID,
        context: str,
    ) -> None:
        key = self._key(tool_id=tool_id, user_id=user_id, context=context)
        session_dir = self._session_dir(key)
        if not session_dir.exists():
            return
        shutil.rmtree(session_dir, ignore_errors=True)

    async def clear_all(self) -> None:
        root = self._sessions_root / "sessions"
        if not root.exists():
            return
        shutil.rmtree(root, ignore_errors=True)

    async def cleanup_expired(self) -> CleanupExpiredSessionFilesResult:
        now = self._clock.now()
        scanned_sessions = 0
        deleted_sessions = 0
        deleted_files = 0
        deleted_bytes = 0

        root = self._sessions_root / "sessions"
        if not root.exists():
            return CleanupExpiredSessionFilesResult(
                scanned_sessions=0,
                deleted_sessions=0,
                deleted_files=0,
                deleted_bytes=0,
            )

        for tool_dir in root.iterdir():
            if not tool_dir.is_dir():
                continue
            for user_dir in tool_dir.iterdir():
                if not user_dir.is_dir():
                    continue
                for context_dir in user_dir.iterdir():
                    if not context_dir.is_dir():
                        continue

                    scanned_sessions += 1
                    meta = self._read_meta(session_dir=context_dir) or {}
                    last_accessed_at_raw = _parse_last_accessed_at(
                        value=meta.get("last_accessed_at")
                    )
                    if last_accessed_at_raw is None:
                        continue

                    try:
                        last_accessed_at = datetime.fromisoformat(last_accessed_at_raw)
                    except ValueError:
                        continue

                    age_seconds = (now - last_accessed_at).total_seconds()
                    if age_seconds <= self._ttl_seconds:
                        continue

                    for item in context_dir.iterdir():
                        if not item.is_file() or item.name == _META_FILENAME:
                            continue
                        try:
                            deleted_bytes += item.stat().st_size
                        except OSError:
                            pass
                        deleted_files += 1

                    shutil.rmtree(context_dir, ignore_errors=True)
                    deleted_sessions += 1

        return CleanupExpiredSessionFilesResult(
            scanned_sessions=scanned_sessions,
            deleted_sessions=deleted_sessions,
            deleted_files=deleted_files,
            deleted_bytes=deleted_bytes,
        )
