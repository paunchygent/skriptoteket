"""Read one picture of an exam workspace document's head revision.

Purpose:
    The editor shows a saved document's pictures from its asset list. Each payload is
    read from the actor-owned head revision's container; a missing document, a picture
    the revision does not declare, or a declared picture without payload is not found.

Relationships:
    - Uses the same versioned container store as the reopen and save handlers.
    - Served by ``web/api/v1/apps_conversion_hub_exam_workspace_assets``.
"""

from __future__ import annotations

from uuid import UUID

from skriptoteket.application.curated_apps.handlers.exam_workspace_document_store import (
    ExamWorkspaceDocumentStore,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_documents import (
    _document_not_found,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.exam_workspace import (
    ExamWorkspaceAssetContent,
    ExamWorkspaceContainerCodecProtocol,
)
from skriptoteket.protocols.vault import VaultFileRepositoryProtocol


def _asset_not_found(lineage_id: UUID, asset_id: str) -> DomainError:
    return DomainError(
        code=ErrorCode.NOT_FOUND,
        message="Bilden finns inte.",
        details={"lineage_id": str(lineage_id), "asset_id": asset_id},
    )


class GetExamWorkspaceAssetHandler:
    """Read one picture payload from the actor-owned head document revision."""

    def __init__(
        self,
        *,
        vault_files: VaultFileRepositoryProtocol,
        codec: ExamWorkspaceContainerCodecProtocol,
        store: ExamWorkspaceDocumentStore,
    ) -> None:
        self._vault_files = vault_files
        self._codec = codec
        self._store = store

    async def handle(
        self, *, actor: User, lineage_id: UUID, asset_id: str
    ) -> ExamWorkspaceAssetContent:
        async with self._store.transaction(user_id=actor.id, lineage_id=lineage_id):
            await self._vault_files.lock_document_lineage(
                user_id=actor.id, document_lineage_id=lineage_id
            )
            return await self._read(actor=actor, lineage_id=lineage_id, asset_id=asset_id)

    async def _read(
        self, *, actor: User, lineage_id: UUID, asset_id: str
    ) -> ExamWorkspaceAssetContent:
        head = await self._vault_files.get_document_head(
            user_id=actor.id, document_lineage_id=lineage_id
        )
        if head is None:
            raise _document_not_found(lineage_id)
        content = await self._store.load(actor=actor, vault_file=head)
        container = self._codec.parse(content=content)
        history = await self._store.get_history(actor=actor, lineage_id=lineage_id)
        containers = [container]
        containers.extend(
            self._codec.parse(content=step.content) for step in (history.baseline, *history.steps)
        )
        asset = next(
            (
                candidate
                for retained in containers
                for candidate in retained.document.assets
                if candidate.asset_id == asset_id
            ),
            None,
        )
        payload = next(
            (
                retained.assets_by_id[asset_id]
                for retained in containers
                if asset_id in retained.assets_by_id
            ),
            None,
        )
        if asset is None or payload is None:
            raise _asset_not_found(lineage_id, asset_id)
        return ExamWorkspaceAssetContent(content=payload, media_type=asset.media_type)
