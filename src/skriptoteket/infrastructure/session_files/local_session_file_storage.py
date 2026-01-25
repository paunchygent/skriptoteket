from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from uuid import UUID, uuid4

from skriptoteket.domain.errors import validation_error
from skriptoteket.domain.scripting.input_files import sanitize_input_filename
from skriptoteket.domain.scripting.tool_sessions import normalize_tool_session_context
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.session_files import (
    CleanupExpiredSessionFilesResult,
    SessionFileContent,
    SessionFileMetadata,
    SessionFileStorageProtocol,
)

_META_FILENAME = "meta.json"


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


def _parse_file_meta(*, value: object) -> list[SessionFileMetadata]:
    if not isinstance(value, list):
        return []
    items: list[SessionFileMetadata] = []
    for raw in value:
        if not isinstance(raw, dict):
            continue
        name = raw.get("name")
        size = raw.get("bytes")
        field = raw.get("field")
        if not isinstance(name, str) or not name.strip():
            continue
        if isinstance(size, bool) or not isinstance(size, int):
            size = 0
        if not isinstance(field, str) or not field.strip():
            field = None
        items.append(SessionFileMetadata(name=name, bytes=size, field=field))
    return items


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

    def _build_meta(
        self,
        *,
        key: _SessionKey,
        now_iso: str,
        files_meta: list[SessionFileMetadata] | None = None,
    ) -> dict[str, object]:
        payload: dict[str, object] = {
            "context": key.context,
            "context_key": key.context_key,
            "last_accessed_at": now_iso,
        }
        if files_meta is not None:
            payload["files"] = [
                {"name": item.name, "bytes": item.bytes, "field": item.field} for item in files_meta
            ]
        return payload

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
        files: list[SessionFileContent],
    ) -> None:
        if not files:
            raise validation_error("files is required")

        key = self._key(tool_id=tool_id, user_id=user_id, context=context)
        normalized_files: list[SessionFileContent] = []
        seen: set[str] = set()
        collisions: dict[str, list[str]] = {}
        for file in files:
            safe_name = sanitize_input_filename(input_filename=file.name)
            if safe_name in seen:
                collisions.setdefault(safe_name, []).append(file.name)
                continue
            seen.add(safe_name)
            normalized_files.append(
                SessionFileContent(
                    name=safe_name,
                    content=file.content,
                    field=file.field,
                )
            )
        if collisions:
            raise validation_error(
                "Duplicate input filenames after sanitization; rename files locally.",
                details={
                    "collisions": {
                        safe_name: [safe_name, *originals]
                        for safe_name, originals in collisions.items()
                    }
                },
            )

        session_dir = self._session_dir(key)
        parent_dir = session_dir.parent
        parent_dir.mkdir(parents=True, exist_ok=True)

        temp_dir = parent_dir / f"{key.context_key}.tmp-{uuid4()}"
        old_dir: Path | None = None

        now_iso = self._clock.now().isoformat()
        files_meta = [
            SessionFileMetadata(name=item.name, bytes=len(item.content), field=item.field)
            for item in normalized_files
        ]
        temp_dir.mkdir(parents=True, exist_ok=False)
        try:
            for item in normalized_files:
                (temp_dir / item.name).write_bytes(item.content)

            _safe_write_json(
                path=self._meta_path(temp_dir),
                payload=self._build_meta(key=key, now_iso=now_iso, files_meta=files_meta),
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
    ) -> list[SessionFileContent]:
        key = self._key(tool_id=tool_id, user_id=user_id, context=context)
        session_dir = self._session_dir(key)
        if not session_dir.exists():
            return []

        meta = self._read_meta(session_dir=session_dir) or {}
        meta_files = _parse_file_meta(value=meta.get("files"))
        field_by_name = {item.name: item.field for item in meta_files}

        files: list[SessionFileContent] = []
        for item in sorted(session_dir.iterdir(), key=lambda path: path.name):
            if item.name == _META_FILENAME:
                continue
            if not item.is_file():
                continue
            field = field_by_name.get(item.name)
            if field is None:
                continue
            files.append(
                SessionFileContent(
                    name=item.name,
                    content=item.read_bytes(),
                    field=field,
                )
            )

        now_iso = self._clock.now().isoformat()
        _safe_write_json(
            path=self._meta_path(session_dir),
            payload=self._build_meta(key=key, now_iso=now_iso, files_meta=meta_files or None),
        )
        return files

    async def get_files_by_name(
        self,
        *,
        tool_id: UUID,
        user_id: UUID,
        context: str,
        names: list[str],
    ) -> list[SessionFileContent]:
        if not names:
            return []

        key = self._key(tool_id=tool_id, user_id=user_id, context=context)
        session_dir = self._session_dir(key)
        if not session_dir.exists():
            return []

        meta = self._read_meta(session_dir=session_dir) or {}
        meta_files = _parse_file_meta(value=meta.get("files"))
        field_by_name = {item.name: item.field for item in meta_files}

        safe_names = [sanitize_input_filename(input_filename=name) for name in names]
        unique_names = set(safe_names)

        files: list[SessionFileContent] = []
        for name in sorted(unique_names):
            path = session_dir / name
            if not path.is_file():
                continue
            field = field_by_name.get(name)
            if field is None:
                continue
            files.append(
                SessionFileContent(
                    name=name,
                    content=path.read_bytes(),
                    field=field,
                )
            )

        now_iso = self._clock.now().isoformat()
        _safe_write_json(
            path=self._meta_path(session_dir),
            payload=self._build_meta(key=key, now_iso=now_iso, files_meta=meta_files or None),
        )
        return files

    async def upsert_files(
        self,
        *,
        tool_id: UUID,
        user_id: UUID,
        context: str,
        files: list[SessionFileContent],
    ) -> None:
        if not files:
            raise validation_error("files is required")

        existing = await self.get_files(
            tool_id=tool_id,
            user_id=user_id,
            context=context,
        )
        merged: dict[str, SessionFileContent] = {item.name: item for item in existing}
        for item in files:
            merged[item.name] = item

        await self.store_files(
            tool_id=tool_id,
            user_id=user_id,
            context=context,
            files=list(merged.values()),
        )

    async def list_files(
        self,
        *,
        tool_id: UUID,
        user_id: UUID,
        context: str,
    ) -> list[SessionFileMetadata]:
        key = self._key(tool_id=tool_id, user_id=user_id, context=context)
        session_dir = self._session_dir(key)
        if not session_dir.exists():
            return []

        meta = self._read_meta(session_dir=session_dir) or {}
        meta_files = _parse_file_meta(value=meta.get("files"))
        field_by_name = {item.name: item.field for item in meta_files}

        files: list[SessionFileMetadata] = []
        for item in sorted(session_dir.iterdir(), key=lambda path: path.name):
            if item.name == _META_FILENAME:
                continue
            if not item.is_file():
                continue
            try:
                size_bytes = item.stat().st_size
            except OSError:
                size_bytes = 0
            files.append(
                SessionFileMetadata(
                    name=item.name,
                    bytes=size_bytes,
                    field=field_by_name.get(item.name),
                )
            )

        now_iso = self._clock.now().isoformat()
        _safe_write_json(
            path=self._meta_path(session_dir),
            payload=self._build_meta(key=key, now_iso=now_iso, files_meta=files),
        )
        return files

    async def delete_files(
        self,
        *,
        tool_id: UUID,
        user_id: UUID,
        context: str,
        names: list[str],
    ) -> int:
        if not names:
            return 0

        key = self._key(tool_id=tool_id, user_id=user_id, context=context)
        session_dir = self._session_dir(key)
        if not session_dir.exists():
            return 0

        safe_names = []
        seen: set[str] = set()
        for name in names:
            safe_name = sanitize_input_filename(input_filename=name)
            if safe_name in seen:
                continue
            seen.add(safe_name)
            safe_names.append(safe_name)

        deleted = 0
        for name in safe_names:
            path = session_dir / name
            if not path.is_file():
                continue
            try:
                path.unlink()
            except OSError:
                continue
            deleted += 1

        meta = self._read_meta(session_dir=session_dir) or {}
        meta_files = _parse_file_meta(value=meta.get("files"))
        remaining_meta = [item for item in meta_files if item.name not in set(safe_names)]

        now_iso = self._clock.now().isoformat()
        _safe_write_json(
            path=self._meta_path(session_dir),
            payload=self._build_meta(key=key, now_iso=now_iso, files_meta=remaining_meta),
        )
        return deleted

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
