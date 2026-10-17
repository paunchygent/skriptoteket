from __future__ import annotations

from uuid import UUID

from skriptoteket.domain.scripting.vault import VaultFile
from skriptoteket.protocols.vault import VaultFileRepositoryProtocol


async def lock_vault_lifecycle_target(
    *, vault_files: VaultFileRepositoryProtocol, user_id: UUID, file_id: UUID
) -> VaultFile | None:
    """Read a lifecycle target under lineage, row, then usage lock ordering.

    The initial read only discovers the immutable lineage. Both active and trashed
    targets must be read again under row locks: cleanup may have purged a selected
    row, or another request may have changed its lifecycle while we waited.
    Callers acquire any usage lock only after this function returns.
    """
    target = await vault_files.get_by_id(file_id=file_id)
    if target is None or target.user_id != user_id:
        return None
    if target.document_lineage_id is not None:
        await vault_files.lock_document_lineage(
            user_id=user_id, document_lineage_id=target.document_lineage_id
        )
    members = await vault_files.lock_lifecycle_rows(
        user_id=user_id,
        file_id=file_id,
        document_lineage_id=target.document_lineage_id,
    )
    return next((member for member in members if member.id == file_id), None)
