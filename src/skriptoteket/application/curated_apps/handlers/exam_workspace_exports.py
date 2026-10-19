"""On-demand exports for native exam workspace documents (D3/S4).

Every target runs the S4 export gate first: items needing review or
carrying unreviewed machine-proposed keys block every target alike. QTI,
DOCX and the Exam.net import PDF ride the existing fail-closed writers and
validators; the student and facit print PDFs render the house-template print
HTML (W1) through the print renderer. The rendering itself lives in
``ExamWorkspaceExportRenderer`` so stateless guest routes reuse it exactly.
"""

from __future__ import annotations

from uuid import UUID, uuid4

from skriptoteket.application.curated_apps.exam_workspace import (
    ExamWorkspaceExportChecklistResponse,
    ExamWorkspaceExportFile,
    ExamWorkspaceExportTarget,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_document_store import (
    ExamWorkspaceDocumentStore,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_export_renderer import (
    ExamWorkspaceExportRenderer,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_head_reader import (
    read_exam_workspace_head,
)
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.vault import VaultFile
from skriptoteket.protocols.exam_workspace import (
    ExamWorkspaceContainerCodecProtocol,
)
from skriptoteket.protocols.vault import VaultFileRepositoryProtocol

_HEAD_CONFLICT_MESSAGE = "Det sparade provet har ändrats. Exportera den aktuella versionen igen."


class ExportExamWorkspaceDocumentHandler:
    """Generate one validated export file, or the package's import loss checklist."""

    def __init__(
        self,
        *,
        vault_files: VaultFileRepositoryProtocol,
        codec: ExamWorkspaceContainerCodecProtocol,
        store: ExamWorkspaceDocumentStore,
        renderer: ExamWorkspaceExportRenderer,
    ) -> None:
        self._vault_files = vault_files
        self._codec = codec
        self._store = store
        self._renderer = renderer

    async def handle(
        self,
        *,
        actor: User,
        lineage_id: UUID,
        target: ExamWorkspaceExportTarget,
        expected_revision: int,
    ) -> ExamWorkspaceExportFile:
        _head, container = await read_exam_workspace_head(
            store=self._store,
            vault_files=self._vault_files,
            codec=self._codec,
            actor=actor,
            lineage_id=lineage_id,
            expected_revision=expected_revision,
            conflict_message=_HEAD_CONFLICT_MESSAGE,
        )
        return self._renderer.render(
            document=container.document,
            assets_by_id=container.assets_by_id,
            target=target,
        )

    async def save(
        self,
        *,
        actor: User,
        lineage_id: UUID,
        target: ExamWorkspaceExportTarget,
        expected_revision: int,
    ) -> VaultFile:
        """Save through the download gate; replace this exam's previous format file."""
        async with self._store.transaction(user_id=actor.id, lineage_id=lineage_id):
            await self._vault_files.lock_document_lineage(
                user_id=actor.id, document_lineage_id=lineage_id
            )
            exported = await self.handle(
                actor=actor,
                lineage_id=lineage_id,
                target=target,
                expected_revision=expected_revision,
            )
            return await self._store.save(
                actor=actor,
                file_id=uuid4(),
                name=exported.filename,
                content=exported.content,
                lineage_id=lineage_id,
                version=expected_revision,
                export_format=target.value,
            )

    async def checklist(
        self, *, actor: User, lineage_id: UUID, expected_revision: int
    ) -> ExamWorkspaceExportChecklistResponse:
        """List losses only while the exported revision is still the saved head."""

        _head, container = await read_exam_workspace_head(
            store=self._store,
            vault_files=self._vault_files,
            codec=self._codec,
            actor=actor,
            lineage_id=lineage_id,
            expected_revision=expected_revision,
            conflict_message=_HEAD_CONFLICT_MESSAGE,
        )
        return self._renderer.checklist(
            document=container.document,
            assets_by_id=container.assets_by_id,
        )
