"""Read exam workspace state behind its lineage lock (W5).

The export handler and the print preview need the actor-owned head revision's
parsed container under the same lineage lock and the same ``expected_revision``
guard. The print preview renders the retained history step the editor names, so
it reads the head plus the history and is guarded by both the saved head
revision and the history cursor. Each caller passes the conflict message a
teacher sees; the shared loaders keep one transaction, lock, head read,
not-found, parse, revision-conflict and cursor-conflict path.
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


def refuse_stale_revision(
    *, revision: int | None, expected_revision: int, conflict_message: str
) -> None:
    """Refuse a head whose revision moved past the caller's ``expected_revision``."""
    if revision != expected_revision:
        raise DomainError(
            code=ErrorCode.CONFLICT,
            message=conflict_message,
            details={
                "expected_revision": expected_revision,
                "current_revision": revision,
            },
        )


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
        refuse_stale_revision(
            revision=container.document.revision,
            expected_revision=expected_revision,
            conflict_message=conflict_message,
        )
        return head, container


async def read_exam_workspace_working_state(
    *,
    store: ExamWorkspaceDocumentStore,
    vault_files: VaultFileRepositoryProtocol,
    codec: ExamWorkspaceContainerCodecProtocol,
    actor: User,
    lineage_id: UUID,
    expected_revision: int,
    expected_cursor: UUID,
    step_id: UUID,
    conflict_message: str,
) -> ExamWorkspaceContainerContent:
    """Lock the lineage, render the requested retained history step, and refuse stale guards.

    The saved head revision is the file's concurrency guard; the history cursor
    guards which working snapshot the editor saw, so an edit autosaved as an
    undo step renders without writing the teacher's saved file. The rendered
    step is named explicitly by ``step_id`` (baseline or stored step), because
    undo navigation in the SPA only moves the editor's local position and never
    the server's cursor. The returned container carries that step's document
    with the saved head revision.
    """
    async with store.transaction(user_id=actor.id, lineage_id=lineage_id):
        await vault_files.lock_document_lineage(user_id=actor.id, document_lineage_id=lineage_id)
        head = await vault_files.get_document_head(user_id=actor.id, document_lineage_id=lineage_id)
        if head is None:
            raise document_not_found(lineage_id)
        content = await store.load(actor=actor, vault_file=head)
        container = codec.parse(content=content)
        refuse_stale_revision(
            revision=container.document.revision,
            expected_revision=expected_revision,
            conflict_message=conflict_message,
        )
        history = await store.get_history(actor=actor, lineage_id=lineage_id)
        if history.cursor != expected_cursor:
            raise DomainError(
                code=ErrorCode.CONFLICT,
                message=conflict_message,
                details={
                    "expected_cursor": str(expected_cursor),
                    "current_cursor": str(history.cursor),
                },
            )
        step = next(
            (
                candidate
                for candidate in (history.baseline, *history.steps)
                if candidate.step_id == step_id
            ),
            None,
        )
        if step is None:
            raise DomainError(
                code=ErrorCode.CONFLICT,
                message=conflict_message,
                details={"step_id": str(step_id)},
            )
        selected = codec.parse(content=step.content)
    document = selected.document.model_copy(update={"revision": head.document_version})
    return selected.model_copy(update={"document": document})
