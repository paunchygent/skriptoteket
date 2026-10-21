"""Create one blank native exam in the teacher's Mina filer (TASK-SKRIPT-40-04-21).

Purpose:
    Give a signed-in teacher the same one-click empty exam guests start from:
    build the blank native document and save revision one to Mina filer
    synchronously, exactly like the QTI import lane saves its revision one.

Relationships:
    - Builds the document with ``domain.exam_workspace.native_exam_blank``,
      which owns the valid empty shape (empty title, one empty question).
    - Names the file with ``exam_document_file_name`` from
      ``application.curated_apps.exam_workspace_file_name`` so an untitled exam
      saves as "Namnlöst prov.provdokument.zip" while the title stays empty.
    - Reuses ``document_summary`` and ``ExamWorkspaceDocumentStore.save``
      inside a store transaction so a reopen sees the same revision-one
      baseline the DOCX, DigiExam and QTI imports write.
"""

from __future__ import annotations

from skriptoteket.application.curated_apps.exam_workspace import ExamWorkspaceDocumentSummary
from skriptoteket.application.curated_apps.exam_workspace_file_name import (
    exam_document_file_name,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_document_store import (
    ExamWorkspaceDocumentStore,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_documents import (
    document_summary,
)
from skriptoteket.domain.curated_apps.exam_workspace.container import (
    ExamWorkspaceContainerContent,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_blank import (
    blank_native_exam_document,
)
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.exam_workspace import ExamWorkspaceContainerCodecProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol


class CreateBlankExamWorkspaceDocumentHandler:
    """Build the blank exam and save it as revision one in Mina filer."""

    def __init__(
        self,
        *,
        store: ExamWorkspaceDocumentStore,
        codec: ExamWorkspaceContainerCodecProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._store = store
        self._codec = codec
        self._id_generator = id_generator

    async def handle(self, *, actor: User) -> ExamWorkspaceDocumentSummary:
        document = blank_native_exam_document()
        lineage_id = document.document_id
        encoded = self._codec.build(content=ExamWorkspaceContainerContent(document=document))
        async with self._store.transaction(user_id=actor.id, lineage_id=lineage_id):
            vault_file = await self._store.save(
                actor=actor,
                file_id=self._id_generator.new_uuid(),
                name=exam_document_file_name(document),
                content=encoded,
                lineage_id=lineage_id,
                version=1,
            )
        return document_summary(vault_file, document)
