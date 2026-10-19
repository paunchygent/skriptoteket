"""Per-step undo rows and once-per-exam pictures, behind the caller's lineage lock.

The exam file stays the durable payload; these rows keep the undo history next
to it: one history head row (the cursor and the editor's position), one row per
retained step (its document without picture bytes, compressed), and one row per
picture the exam names. One autosave inserts one step row and moves the head
row; it never reads or rewrites other step rows. A position move updates only
the head row. A picture no retained step, no baseline and no current file uses
is deleted when the step that last used it is trimmed.
Relationships: owned by ``ExamWorkspaceDocumentStore``; the undo-step handler
reaches these rows through the store, never directly.
"""

from __future__ import annotations

from uuid import UUID

from skriptoteket.application.curated_apps.exam_workspace_history import (
    MAX_RETAINED_UNDO_STEPS,
    ExamWorkspaceHistoryCursor,
    ExamWorkspaceHistoryResponse,
    ExamWorkspaceHistoryState,
    ExamWorkspaceHistoryStep,
    history_response_for,
    stored_step,
)
from skriptoteket.domain.curated_apps.exam_workspace.container import ExamWorkspaceContainerContent
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import NativeExamDocument
from skriptoteket.domain.errors import DomainError, ErrorCode, validation_error
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.exam_workspace import ExamWorkspaceContainerCodecProtocol
from skriptoteket.protocols.vault import VaultFileRepositoryProtocol, VaultStorageProtocol


class ExamWorkspaceHistoryRowStore:
    """Undo history rows for one exam file; the caller holds the lineage lock."""

    def __init__(
        self,
        *,
        vault_files: VaultFileRepositoryProtocol,
        vault_storage: VaultStorageProtocol,
        codec: ExamWorkspaceContainerCodecProtocol,
    ) -> None:
        self._vault_files = vault_files
        self._vault_storage = vault_storage
        self._codec = codec

    async def ensure_head(self, *, actor: User, lineage_id: UUID) -> ExamWorkspaceHistoryCursor:
        """Read the exam's history head row, recreating the baseline from the file if missing.

        The step-storage migration drops the old history blob rows; the first open
        after it rebuilds the baseline from the saved file, so the app keeps opening.
        """
        head = await self._vault_files.get_history_head(
            user_id=actor.id, document_lineage_id=lineage_id
        )
        if head is not None:
            return head
        state = await self.create_baseline_from_file(actor=actor, lineage_id=lineage_id)
        return ExamWorkspaceHistoryCursor(
            cursor=state.cursor,
            current_step_id=state.current_step_id,
            baseline_step_id=state.baseline.step_id,
        )

    async def create_baseline_from_file(
        self, *, actor: User, lineage_id: UUID
    ) -> ExamWorkspaceHistoryState:
        head = await self._vault_files.get_document_head(
            user_id=actor.id, document_lineage_id=lineage_id
        )
        if head is None:
            raise validation_error("Den sparade redigeringshistoriken saknas.")
        content = await self._vault_storage.read_file(user_id=actor.id, file_id=head.id)
        container = self._codec.parse(content=content)
        if (
            container.document.document_id != lineage_id
            or container.document.revision != head.document_version
        ):
            raise validation_error("Den sparade dokumentversionen är skadad.")
        return await self.init_history(actor=actor, lineage_id=lineage_id, content=content)

    async def init_history(
        self, *, actor: User, lineage_id: UUID, content: bytes
    ) -> ExamWorkspaceHistoryState:
        """Store the baseline step row for a new exam and return its initial state."""
        container = self._codec.parse(content=content)
        head = ExamWorkspaceHistoryCursor(
            cursor=lineage_id, current_step_id=lineage_id, baseline_step_id=lineage_id
        )
        await self._vault_files.upsert_history_head(
            user_id=actor.id, document_lineage_id=lineage_id, head=head
        )
        await self._vault_files.insert_history_step(
            user_id=actor.id,
            document_lineage_id=lineage_id,
            step=stored_step(
                step_id=lineage_id,
                position=0,
                document=container.document,
                notes=container.notes,
            ),
            assets_by_id=dict(container.assets_by_id),
        )
        return ExamWorkspaceHistoryState(
            cursor=lineage_id,
            current_step_id=lineage_id,
            baseline=ExamWorkspaceHistoryStep(step_id=lineage_id, content=content),
        )

    async def get_state(self, *, actor: User, lineage_id: UUID) -> ExamWorkspaceHistoryState:
        """Rebuild the retained snapshots from their step rows and the picture rows."""
        head = await self._vault_files.get_history_head(
            user_id=actor.id, document_lineage_id=lineage_id
        )
        if head is None:
            return await self.create_baseline_from_file(actor=actor, lineage_id=lineage_id)
        records = await self._vault_files.list_history_steps(
            user_id=actor.id, document_lineage_id=lineage_id
        )
        if not records:
            raise validation_error("Den sparade redigeringshistoriken saknas.")
        wanted = {asset_id for record in records for asset_id in record.asset_ids}
        pictures = await self._vault_files.get_history_assets(
            user_id=actor.id,
            document_lineage_id=lineage_id,
            asset_ids=tuple(sorted(wanted)),
        )
        snapshots: list[ExamWorkspaceHistoryStep] = []
        for record in records:
            missing = sorted(set(record.asset_ids) - pictures.keys())
            if missing:
                raise validation_error(
                    "Dokumentet hänvisar till bilder som saknas.",
                    details={"missing_assets": missing},
                )
            snapshots.append(
                ExamWorkspaceHistoryStep(
                    step_id=record.step_id,
                    content=self._codec.build(
                        content=ExamWorkspaceContainerContent(
                            document=record.document,
                            assets_by_id={
                                asset_id: pictures[asset_id] for asset_id in record.asset_ids
                            },
                            notes=record.notes,
                        )
                    ),
                )
            )
        baseline = next(
            (snapshot for snapshot in snapshots if snapshot.step_id == head.baseline_step_id),
            None,
        )
        if baseline is None:
            raise validation_error("Den sparade redigeringshistoriken saknas.")
        return ExamWorkspaceHistoryState(
            cursor=head.cursor,
            current_step_id=head.current_step_id,
            baseline=baseline,
            steps=tuple(
                snapshot for snapshot in snapshots if snapshot.step_id != head.baseline_step_id
            ),
        )

    async def replace_state(
        self, *, actor: User, lineage_id: UUID, history: ExamWorkspaceHistoryState
    ) -> None:
        """Replace every step row, used when conversion delivery rewrites all snapshots."""
        snapshots = (history.baseline, *history.steps)
        containers = [self._codec.parse(content=snapshot.content) for snapshot in snapshots]
        await self._vault_files.upsert_history_head(
            user_id=actor.id,
            document_lineage_id=lineage_id,
            head=ExamWorkspaceHistoryCursor(
                cursor=history.cursor,
                current_step_id=history.current_step_id,
                baseline_step_id=history.baseline.step_id,
            ),
        )
        refs = await self._vault_files.list_history_step_refs(
            user_id=actor.id, document_lineage_id=lineage_id
        )
        await self._vault_files.delete_history_steps(
            user_id=actor.id,
            document_lineage_id=lineage_id,
            step_ids=[ref.step_id for ref in refs],
        )
        for position, (snapshot, container) in enumerate(zip(snapshots, containers, strict=True)):
            await self._vault_files.insert_history_step(
                user_id=actor.id,
                document_lineage_id=lineage_id,
                step=stored_step(
                    step_id=snapshot.step_id,
                    position=position,
                    document=container.document,
                    notes=container.notes,
                ),
                assets_by_id=dict(container.assets_by_id),
            )
        await self._collect_orphan_pictures(
            actor=actor,
            lineage_id=lineage_id,
            keep={asset_id for container in containers for asset_id in container.assets_by_id},
        )

    async def append_step(
        self,
        *,
        actor: User,
        lineage_id: UUID,
        head: ExamWorkspaceHistoryCursor,
        step_id: UUID,
        document: NativeExamDocument,
        assets_by_id: dict[str, bytes],
        notes: tuple[str, ...],
        after_step_id: UUID,
    ) -> ExamWorkspaceHistoryResponse:
        """Insert one step row, drop redo steps and trim past the limit, then move the head row.

        Other step rows are never read or rewritten: the listing carries only ids,
        positions and asset references, never step documents.
        """
        refs = await self._vault_files.list_history_step_refs(
            user_id=actor.id, document_lineage_id=lineage_id
        )
        positions = {ref.step_id: ref.position for ref in refs}
        if after_step_id not in positions:
            raise DomainError(code=ErrorCode.CONFLICT, message="Ångrasteget finns inte längre.")
        after_position = positions[after_step_id]
        dropped = [ref.step_id for ref in refs if ref.position > after_position]
        if dropped:
            await self._vault_files.delete_history_steps(
                user_id=actor.id, document_lineage_id=lineage_id, step_ids=dropped
            )
        await self._vault_files.insert_history_step(
            user_id=actor.id,
            document_lineage_id=lineage_id,
            step=stored_step(
                step_id=step_id, position=after_position + 1, document=document, notes=notes
            ),
            assets_by_id=assets_by_id,
        )
        refs = await self._vault_files.list_history_step_refs(
            user_id=actor.id, document_lineage_id=lineage_id
        )
        retained = [ref for ref in refs if ref.step_id != head.baseline_step_id]
        victims: list[UUID] = []
        if len(retained) > MAX_RETAINED_UNDO_STEPS:
            victims = [ref.step_id for ref in retained[: len(retained) - MAX_RETAINED_UNDO_STEPS]]
            await self._vault_files.delete_history_steps(
                user_id=actor.id, document_lineage_id=lineage_id, step_ids=victims
            )
            refs = [ref for ref in refs if ref.step_id not in victims]
        if dropped or victims:
            await self._collect_orphan_pictures(
                actor=actor,
                lineage_id=lineage_id,
                keep={asset_id for ref in refs for asset_id in ref.asset_ids},
            )
        updated = head.model_copy(update={"cursor": step_id, "current_step_id": step_id})
        await self._vault_files.upsert_history_head(
            user_id=actor.id, document_lineage_id=lineage_id, head=updated
        )
        return history_response_for(head=updated, refs=refs)

    async def move_position(
        self,
        *,
        actor: User,
        lineage_id: UUID,
        head: ExamWorkspaceHistoryCursor,
        step_id: UUID,
        new_cursor: UUID,
    ) -> ExamWorkspaceHistoryResponse:
        """Move the editor's position; the only write is the history head row."""
        refs = await self._vault_files.list_history_step_refs(
            user_id=actor.id, document_lineage_id=lineage_id
        )
        if all(ref.step_id != step_id for ref in refs):
            raise DomainError(code=ErrorCode.NOT_FOUND, message="Ångrasteget finns inte.")
        updated = head.model_copy(update={"cursor": new_cursor, "current_step_id": step_id})
        await self._vault_files.upsert_history_head(
            user_id=actor.id, document_lineage_id=lineage_id, head=updated
        )
        return history_response_for(head=updated, refs=refs)

    async def step_document(
        self, *, actor: User, lineage_id: UUID, step_id: UUID
    ) -> NativeExamDocument:
        record = await self._vault_files.get_history_step(
            user_id=actor.id, document_lineage_id=lineage_id, step_id=step_id
        )
        if record is None:
            raise DomainError(code=ErrorCode.NOT_FOUND, message="Ångrasteget finns inte.")
        return record.document

    async def _collect_orphan_pictures(
        self, *, actor: User, lineage_id: UUID, keep: set[str]
    ) -> None:
        """Delete pictures no retained step, baseline or current file uses anymore."""
        head = await self._vault_files.get_document_head(
            user_id=actor.id, document_lineage_id=lineage_id
        )
        if head is not None:
            container = self._codec.parse(
                content=await self._vault_storage.read_file(user_id=actor.id, file_id=head.id)
            )
            keep |= set(container.assets_by_id)
        await self._vault_files.delete_orphan_history_assets(
            user_id=actor.id, document_lineage_id=lineage_id, keep_asset_ids=frozenset(keep)
        )
