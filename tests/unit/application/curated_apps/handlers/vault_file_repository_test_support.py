from datetime import datetime
from uuid import UUID

from skriptoteket.domain.scripting.vault import VaultFile, VaultListSort, VaultListState


class InMemoryVaultFileRepository:
    def __init__(self) -> None:
        self.files: dict[UUID, VaultFile] = {}

    async def get_by_id(self, *, file_id: UUID) -> VaultFile | None:
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
        del state, search, sort, limit, offset
        return [file for file in self.files.values() if file.user_id == user_id]

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
        del cutoff, limit
        return []

    async def get_document_head(
        self, *, user_id: UUID, document_lineage_id: UUID
    ) -> VaultFile | None:
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
            and file.deleted_at is None
            and (file.source_artifact_id or "").startswith(source_artifact_prefix)
        }
        return sorted(heads.values(), key=lambda file: (file.created_at, file.id), reverse=True)

    async def lock_document_lineage(self, *, user_id: UUID, document_lineage_id: UUID) -> None:
        return None

    async def create(self, *, file: VaultFile) -> VaultFile:
        self.files[file.id] = file
        return file

    async def update(self, *, file: VaultFile) -> VaultFile:
        self.files[file.id] = file
        return file

    async def delete(self, *, file_id: UUID) -> None:
        self.files.pop(file_id, None)
