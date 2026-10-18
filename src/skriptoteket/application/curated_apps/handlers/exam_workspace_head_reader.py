"""Read the saved head revision of one exam workspace document behind its lineage lock.

Both the export handler and the print preview handler need the actor-owned head
revision's parsed container under the same lineage lock and the same
``expected_revision`` guard. They differ only in the conflict message a teacher
sees, so each passes its own; the shared loader keeps one transaction, lock, head
read, not-found, parse and revision-conflict path.
"""

from __future__ import annotations

from uuid import UUID

from skriptoteket.application.curated_apps.handlers.exam_workspace_document_store import (
    ExamWorkspaceDocumentStore,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_documents import (
    document_not_found,
)
from skriptoteket.domain.curated_apps.exam_workspace.container import (
    ExamWorkspaceContainerContent,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.vault import VaultFile
from skriptoteket.protocols.exam_workspace import ExamWorkspaceContainerCodecProtocol
from skriptoteket.protocols.vault import VaultFileRepositoryProtocol


async def read_exam_workspace_head(
    *,
    store: ExamWorkspaceDocumentStore,
    vault_files: VaultFileRepositoryProtocol,
    codec: ExamWorkspaceContainerCodecProtocol,
    actor: User,
    lineage_id: UUID,
    expected_revision: int,
    conflict_message: str,
) -> tuple[VaultFile, ExamWorkspaceContainerContent]:
    """Lock the lineage, read its head revision and refuse a stale ``expected_revision``.

    The caller owns ``conflict_message`` because the export handler points at a new
    export while the print preview points at a refreshed preview.
    """
    async with store.transaction(user_id=actor.id, lineage_id=lineage_id):
        await vault_files.lock_document_lineage(user_id=actor.id, document_lineage_id=lineage_id)
        head = await vault_files.get_document_head(user_id=actor.id, document_lineage_id=lineage_id)
        if head is None:
            raise document_not_found(lineage_id)
        content = await store.load(actor=actor, vault_file=head)
        container = codec.parse(content=content)
        if container.document.revision != expected_revision:
            raise DomainError(
                code=ErrorCode.CONFLICT,
                message=conflict_message,
                details={
                    "expected_revision": expected_revision,
                    "current_revision": container.document.revision,
                },
            )
        return head, container
