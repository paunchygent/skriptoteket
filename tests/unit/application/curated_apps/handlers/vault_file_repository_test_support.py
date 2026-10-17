import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from uuid import UUID

from skriptoteket.domain.scripting.vault import VaultFile, VaultListSort, VaultListState


def _matches_search(name: str, search: str) -> bool:
    """Interpret the repository's ILIKE %search% pattern, including SQL escapes."""
    parts: list[str] = []
    tokens = iter(f"%{search}%")
    for token in tokens:
        if token == "\\":
            parts.append(re.escape(next(tokens)))
        elif token == "%":
            parts.append(".*")
        elif token == "_":
            parts.append(".")
        else:
            parts.append(re.escape(token))
    return re.fullmatch("".join(parts), name, flags=re.IGNORECASE | re.DOTALL) is not None


class InMemoryVaultFileRepository:
    def __init__(self) -> None:
        self.files: dict[UUID, VaultFile] = {}
        self.histories: dict[tuple[UUID, UUID], bytes] = {}
        self.calls: list[tuple[str, dict[str, object]]] = []

    async def get_by_id(self, *, file_id: UUID) -> VaultFile | None:
        self.calls.append(("get_by_id", {"file_id": file_id}))
        return self.files.get(file_id)

    async def list_for_user(
        self,
        *,
        user_id: UUID,
        state: VaultListState,
        search: str | None,
        sort: VaultListSort,
        limit: int,
        offset: int,
    ) -> list[VaultFile]:
        files = [
            file
            for file in self.files.values()
            if file.user_id == user_id
            and file.export_format is None
            and (file.deleted_at is None) == (state is VaultListState.ACTIVE)
            and (not search or _matches_search(file.name, search))
        ]
        if sort is VaultListSort.NAME:
            files.sort(key=lambda file: (file.name.lower(), file.id))
        elif sort is VaultListSort.SIZE:
            files.sort(key=lambda file: (file.bytes, file.id), reverse=True)
        else:
            files.sort(key=lambda file: (file.created_at, file.id), reverse=True)
        return files[offset : offset + limit]

    async def list_active_for_user(self, *, user_id: UUID) -> list[VaultFile]:
        return [
            file
            for file in self.files.values()
            if file.user_id == user_id and file.deleted_at is None
        ]

    async def list_by_ids(
        self,
        *,
        user_id: UUID,
        file_ids: list[UUID],
        include_deleted: bool,
    ) -> list[VaultFile]:
        files = [self.files[file_id] for file_id in file_ids if file_id in self.files]
        if include_deleted:
            return [file for file in files if file.user_id == user_id]
        return [file for file in files if file.user_id == user_id and file.deleted_at is None]

    async def list_expired(self, *, cutoff: datetime, limit: int) -> list[VaultFile]:
        expired = [
            file
            for file in self.files.values()
            if file.deleted_at is not None and file.deleted_at < cutoff
        ]
        expired.sort(key=lambda file: (file.deleted_at, file.id))
        return expired[:limit]

    async def get_document_head(
        self, *, user_id: UUID, document_lineage_id: UUID
    ) -> VaultFile | None:
        self.calls.append(
            ("get_document_head", {"user_id": user_id, "document_lineage_id": document_lineage_id})
        )
        heads = await self.list_document_heads(user_id=user_id, source_artifact_prefix="")
        return next((h for h in heads if h.document_lineage_id == document_lineage_id), None)

    async def list_document_heads(
        self, *, user_id: UUID, source_artifact_prefix: str
    ) -> list[VaultFile]:
        # Ascending version order, so each lineage keeps its highest version.
        heads = {
            file.document_lineage_id: file
            for file in sorted(self.files.values(), key=lambda file: file.document_version or 0)
            if file.user_id == user_id
            and file.document_lineage_id is not None
            and file.export_format is None
            and file.deleted_at is None
            and (file.source_artifact_id or "").startswith(source_artifact_prefix)
        }
        return sorted(heads.values(), key=lambda file: (file.created_at, file.id), reverse=True)

    async def name_in_use(
        self,
        *,
        user_id: UUID,
        name: str,
        exclude_lineage_id: UUID | None = None,
        exclude_file_id: UUID | None = None,
    ) -> bool:
        self.calls.append(("name_in_use", {"user_id": user_id, "name": name}))
        return any(
            file.user_id == user_id
            and file.name == name
            and file.deleted_at is None
            and (exclude_lineage_id is None or file.document_lineage_id != exclude_lineage_id)
            and file.id != exclude_file_id
            for file in self.files.values()
        )

    async def list_saved_exports(
        self, *, user_id: UUID, document_lineage_id: UUID
    ) -> list[VaultFile]:
        return [
            file
            for file in self.files.values()
            if file.user_id == user_id
            and file.document_lineage_id == document_lineage_id
            and file.export_format is not None
            and file.deleted_at is None
        ]

    async def list_exam_files(
        self, *, user_id: UUID, document_lineage_id: UUID, include_deleted: bool
    ) -> list[VaultFile]:
        return sorted(
            (
                file
                for file in self.files.values()
                if file.user_id == user_id
                and file.document_lineage_id == document_lineage_id
                and (include_deleted or file.deleted_at is None)
            ),
            key=lambda file: (
                file.export_format is not None,
                file.export_format or "",
                file.created_at,
                file.id,
            ),
        )

    async def get_history(self, *, user_id: UUID, document_lineage_id: UUID) -> bytes | None:
        return self.histories.get((user_id, document_lineage_id))

    async def put_history(
        self, *, user_id: UUID, document_lineage_id: UUID, content: bytes
    ) -> None:
        self.histories[(user_id, document_lineage_id)] = content

    @asynccontextmanager
    async def guard_document_payload(
        self, *, user_id: UUID, document_lineage_id: UUID
    ) -> AsyncIterator[None]:
        """Unit-only port double; real lock ordering is covered by integration tests."""
        yield

    async def lock_owner_renames(self, *, user_id: UUID) -> None:
        self.calls.append(("lock_owner_renames", {"user_id": user_id}))

    async def lock_document_lineage(self, *, user_id: UUID, document_lineage_id: UUID) -> None:
        self.calls.append(
            (
                "lock_document_lineage",
                {"user_id": user_id, "document_lineage_id": document_lineage_id},
            )
        )

    async def rename_active(self, *, user_id: UUID, file_id: UUID, name: str) -> VaultFile | None:
        file = self.files.get(file_id)
        if file is None or file.user_id != user_id or file.deleted_at is not None:
            return None
        renamed = file.model_copy(update={"name": name})
        self.files[file_id] = renamed
        return renamed

    async def rename_lineage(
        self, *, user_id: UUID, document_lineage_id: UUID, name: str
    ) -> list[VaultFile]:
        renamed = [
            file.model_copy(update={"name": name})
            for file in self.files.values()
            if file.user_id == user_id
            and file.document_lineage_id == document_lineage_id
            and file.export_format is None
        ]
        self.files.update((file.id, file) for file in renamed)
        return renamed

    async def create(self, *, file: VaultFile) -> VaultFile:
        self.files[file.id] = file
        return file

    async def update(self, *, file: VaultFile) -> VaultFile:
        current = self.files.get(file.id)
        if current is None:
            return file
        # Lifecycle callers own only trash state; a stale delete/restore payload
        # must not overwrite a concurrently committed name or immutable metadata.
        updated = current.model_copy(
            update={"deleted_at": file.deleted_at, "trashed_with_exam": file.trashed_with_exam}
        )
        self.files[file.id] = updated
        return updated

    async def overwrite(self, *, file: VaultFile) -> VaultFile:
        current = self.files.get(file.id)
        if current is None:
            return file
        overwritten = current.model_copy(
            update={
                "name": file.name,
                "bytes": file.bytes,
                "source_artifact_id": file.source_artifact_id,
                "document_version": file.document_version,
                "export_format": file.export_format,
                "document_saved_at": file.document_saved_at,
            }
        )
        self.files[file.id] = overwritten
        return overwritten

    async def delete(self, *, file_id: UUID) -> None:
        file = self.files.pop(file_id, None)
        if file is not None and file.document_lineage_id is not None and file.export_format is None:
            self.histories.pop((file.user_id, file.document_lineage_id), None)
