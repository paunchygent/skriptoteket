"""Sign-in handoff: save a guest's browser exam draft into Mina filer once (P5).

Purpose:
    After sign-in the browser posts its draft (document JSON + picture bytes +
    the draft's draft_id). One exam is created in the teacher's Mina filer
    through the Spara som creation path; a repeated or concurrent post with the
    same ``(owner_user_id, draft_id)`` creates nothing new and returns the exam
    the first post created.

Relationships:
    - Reuses ``ExamWorkspaceDocumentStore.save`` (the copy path's creation
      function) for the new lineage, vault file, exam container, exam index
      entry, baseline history and the Mina filer quota check.
    - Verifies the posted picture bytes through B2a's verifier in
      ``handlers.public_exam_workspace_exports`` before anything is claimed.
    - The claim ledger lives in ``ExamGuestDraftHandoffModel``; one store
      transaction covers the claim and the creation, so a refused creation
      leaves no ledger row and a failed outermost commit compensates the
      written payload.
"""

from __future__ import annotations

from collections.abc import Mapping
from uuid import UUID

from skriptoteket.application.curated_apps.exam_workspace import ExamWorkspaceDocumentResponse
from skriptoteket.application.curated_apps.handlers.exam_workspace_document_store import (
    ExamWorkspaceDocumentStore,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_documents import document_summary
from skriptoteket.application.curated_apps.handlers.public_exam_workspace_exports import (
    PublicExamWorkspaceExportHandler,
)
from skriptoteket.domain.curated_apps.exam_workspace.container import (
    ExamWorkspaceContainerContent,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_title_numbering import (
    exam_title_base,
    numbered_exam_title,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import NativeExamDocument
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.vault_names import rename_vault_filename
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.exam_index import ExamIndexRepositoryProtocol
from skriptoteket.protocols.exam_workspace import (
    ExamWorkspaceContainerCodecProtocol,
    GetExamWorkspaceDocumentHandlerProtocol,
)
from skriptoteket.protocols.exam_workspace_guest_drafts import (
    ExamGuestDraftHandoffRepositoryProtocol,
)
from skriptoteket.protocols.id_generator import IdGeneratorProtocol

_COPY_EXTENSION = ".provdokument.zip"


class ImportGuestExamDraftHandler:
    """Create the teacher's exam from a guest draft; the first post wins."""

    def __init__(
        self,
        *,
        handoffs: ExamGuestDraftHandoffRepositoryProtocol,
        reader: GetExamWorkspaceDocumentHandlerProtocol,
        codec: ExamWorkspaceContainerCodecProtocol,
        store: ExamWorkspaceDocumentStore,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
        index: ExamIndexRepositoryProtocol,
    ) -> None:
        self._handoffs = handoffs
        self._reader = reader
        self._codec = codec
        self._store = store
        self._clock = clock
        self._id_generator = id_generator
        self._index = index

    async def handle(
        self,
        *,
        actor: User,
        draft_id: UUID,
        document: NativeExamDocument,
        assets_by_id: Mapping[str, bytes],
        notes: tuple[str, ...],
    ) -> ExamWorkspaceDocumentResponse:
        PublicExamWorkspaceExportHandler._require_declared_assets(
            document=document, assets_by_id=assets_by_id
        )
        lineage_id = self._id_generator.new_uuid()
        async with self._store.transaction(user_id=actor.id, lineage_id=lineage_id):
            claimed = await self._handoffs.claim(
                owner_user_id=actor.id,
                draft_id=draft_id,
                lineage_id=lineage_id,
                now=self._clock.now(),
            )
            if not claimed:
                existing = await self._handoffs.get_lineage(
                    owner_user_id=actor.id, draft_id=draft_id
                )
                assert existing is not None  # a lost claim means the winner committed
                return await self._reader.handle(actor=actor, lineage_id=existing)
            numbered = await self._with_unique_title(actor=actor, document=document)
            return await self._create(
                actor=actor,
                lineage_id=lineage_id,
                name=rename_vault_filename(stem=numbered.title, extension=_COPY_EXTENSION),
                document=numbered,
                assets_by_id=assets_by_id,
                notes=notes,
            )

    async def _with_unique_title(
        self, *, actor: User, document: NativeExamDocument
    ) -> NativeExamDocument:
        """Number the draft title against the owner's taken titles under the lock."""
        await self._index.lock_owner_titles(owner_user_id=actor.id)
        taken = await self._index.titles_like(
            owner_user_id=actor.id, base=exam_title_base(document.title)
        )
        return document.model_copy(update={"title": numbered_exam_title(document.title, taken)})

    async def _create(
        self,
        *,
        actor: User,
        lineage_id: UUID,
        name: str,
        document: NativeExamDocument,
        assets_by_id: Mapping[str, bytes],
        notes: tuple[str, ...],
    ) -> ExamWorkspaceDocumentResponse:
        copied = document.model_copy(update={"document_id": lineage_id, "revision": 1})
        content = self._codec.build(
            content=ExamWorkspaceContainerContent(
                document=copied,
                assets_by_id=dict(assets_by_id),
                notes=notes,
            )
        )
        vault_file = await self._store.save(
            actor=actor,
            file_id=self._id_generator.new_uuid(),
            name=name,
            content=content,
            lineage_id=lineage_id,
            version=1,
        )
        return ExamWorkspaceDocumentResponse(
            document=copied,
            saved_document=copied,
            summary=document_summary(vault_file, copied),
            history_cursor=lineage_id,
            notes=notes,
            conversion=None,
        )
