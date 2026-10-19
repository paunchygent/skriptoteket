import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from uuid import UUID

from skriptoteket.application.curated_apps.exam_workspace_history import (
    ExamWorkspaceHistoryCursor,
    ExamWorkspaceHistoryStepRef,
    ExamWorkspaceHistoryStoredStep,
)
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
        self.history_heads: dict[tuple[UUID, UUID], ExamWorkspaceHistoryCursor] = {}
        self.history_steps: dict[tuple[UUID, UUID, UUID], ExamWorkspaceHistoryStoredStep] = {}
        self.history_assets: dict[tuple[UUID, UUID, str], bytes] = {}
        self.calls: list[tuple[str, dict[str, object]]] = []

    async def get_by_id(self, *, file_id: UUID) -> VaultFile | None:
        self.calls.append(("get_by_id", {"file_id": file_id}))
        return self.files.get(file_id)

    async def lock_lifecycle_rows(
        self, *, user_id: UUID, file_id: UUID, document_lineage_id: UUID | None
    ) -> list[VaultFile]:
        self.calls.append(
            (
                "lock_lifecycle_rows",
                {
                    "user_id": user_id,
                    "file_id": file_id,
                    "document_lineage_id": document_lineage_id,
                },
            )
        )
        return sorted(
            (
                file
                for file in self.files.values()
                if file.user_id == user_id
                and (
                    file.document_lineage_id == document_lineage_id
                    if document_lineage_id is not None
                    else file.id == file_id
                )
            ),
            key=lambda file: file.id,
        )

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

    async def get_history_head(
        self, *, user_id: UUID, document_lineage_id: UUID
    ) -> ExamWorkspaceHistoryCursor | None:
        self.calls.append(
            (
                "get_history_head",
                {"user_id": user_id, "document_lineage_id": document_lineage_id},
            )
        )
        return self.history_heads.get((user_id, document_lineage_id))

    async def upsert_history_head(
        self,
        *,
        user_id: UUID,
        document_lineage_id: UUID,
        head: ExamWorkspaceHistoryCursor,
    ) -> None:
        self.calls.append(
            (
                "upsert_history_head",
                {"user_id": user_id, "document_lineage_id": document_lineage_id},
            )
        )
        self.history_heads[(user_id, document_lineage_id)] = head

    async def get_history_step(
        self, *, user_id: UUID, document_lineage_id: UUID, step_id: UUID
    ) -> ExamWorkspaceHistoryStoredStep | None:
        self.calls.append(
            (
                "get_history_step",
                {
                    "user_id": user_id,
                    "document_lineage_id": document_lineage_id,
                    "step_id": step_id,
                },
            )
        )
        return self.history_steps.get((user_id, document_lineage_id, step_id))

    async def list_history_step_refs(
        self, *, user_id: UUID, document_lineage_id: UUID
    ) -> list[ExamWorkspaceHistoryStepRef]:
        self.calls.append(
            (
                "list_history_step_refs",
                {"user_id": user_id, "document_lineage_id": document_lineage_id},
            )
        )
        refs = [
            ExamWorkspaceHistoryStepRef(
                step_id=step_id, position=record.position, asset_ids=record.asset_ids
            )
            for (owner_id, row_lineage, step_id), record in self.history_steps.items()
            if owner_id == user_id and row_lineage == document_lineage_id
        ]
        refs.sort(key=lambda ref: ref.position)
        return refs

    async def list_history_steps(
        self, *, user_id: UUID, document_lineage_id: UUID
    ) -> list[ExamWorkspaceHistoryStoredStep]:
        self.calls.append(
            (
                "list_history_steps",
                {"user_id": user_id, "document_lineage_id": document_lineage_id},
            )
        )
        steps = [
            record
            for (owner_id, row_lineage, _), record in self.history_steps.items()
            if owner_id == user_id and row_lineage == document_lineage_id
        ]
        steps.sort(key=lambda record: record.position)
        return steps

    async def get_history_assets(
        self, *, user_id: UUID, document_lineage_id: UUID, asset_ids: tuple[str, ...]
    ) -> dict[str, bytes]:
        self.calls.append(
            (
                "get_history_assets",
                {"user_id": user_id, "document_lineage_id": document_lineage_id},
            )
        )
        return {
            asset_id: self.history_assets[(user_id, document_lineage_id, asset_id)]
            for asset_id in asset_ids
            if (user_id, document_lineage_id, asset_id) in self.history_assets
        }

    async def insert_history_step(
        self,
        *,
        user_id: UUID,
        document_lineage_id: UUID,
        step: ExamWorkspaceHistoryStoredStep,
        assets_by_id: dict[str, bytes],
    ) -> None:
        self.calls.append(
            (
                "insert_history_step",
                {
                    "user_id": user_id,
                    "document_lineage_id": document_lineage_id,
                    "step_id": step.step_id,
                },
            )
        )
        self.history_steps[(user_id, document_lineage_id, step.step_id)] = step
        for asset_id, content in assets_by_id.items():
            key = (user_id, document_lineage_id, asset_id)
            if key not in self.history_assets:
                self.history_assets[key] = content

    async def delete_history_steps(
        self, *, user_id: UUID, document_lineage_id: UUID, step_ids: list[UUID]
    ) -> None:
        self.calls.append(
            (
                "delete_history_steps",
                {"user_id": user_id, "document_lineage_id": document_lineage_id},
            )
        )
        for step_id in step_ids:
            self.history_steps.pop((user_id, document_lineage_id, step_id), None)

    async def delete_orphan_history_assets(
        self, *, user_id: UUID, document_lineage_id: UUID, keep_asset_ids: frozenset[str]
    ) -> None:
        self.calls.append(
            (
                "delete_orphan_history_assets",
                {"user_id": user_id, "document_lineage_id": document_lineage_id},
            )
        )
        for key in [
            key
            for key in self.history_assets
            if key[:2] == (user_id, document_lineage_id) and key[2] not in keep_asset_ids
        ]:
            del self.history_assets[key]

    async def delete_history(self, *, user_id: UUID, document_lineage_id: UUID) -> None:
        self.calls.append(
            (
                "delete_history",
                {"user_id": user_id, "document_lineage_id": document_lineage_id},
            )
        )
        self.history_heads.pop((user_id, document_lineage_id), None)
        for step_key in [
            step_key
            for step_key in self.history_steps
            if step_key[:2] == (user_id, document_lineage_id)
        ]:
            del self.history_steps[step_key]
        for asset_key in [
            asset_key
            for asset_key in self.history_assets
            if asset_key[:2] == (user_id, document_lineage_id)
        ]:
            del self.history_assets[asset_key]

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
            self.history_heads.pop((file.user_id, file.document_lineage_id), None)
            for step_key in [
                step_key
                for step_key in self.history_steps
                if step_key[:2] == (file.user_id, file.document_lineage_id)
            ]:
                del self.history_steps[step_key]
            for asset_key in [
                key
                for key in self.history_assets
                if key[:2] == (file.user_id, file.document_lineage_id)
            ]:
                del self.history_assets[asset_key]
