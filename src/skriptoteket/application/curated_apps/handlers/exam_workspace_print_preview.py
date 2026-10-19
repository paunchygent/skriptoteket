"""Server-side print preview for native exam workspace documents (W5).

The retained history step the editor names is rendered into one PNG per printed
page through the print renderer, so the Förhandsgranska panel can show the exam
page by page and scroll to the selected question. The saved head revision and
the history cursor both guard the render, and no handler here writes the
teacher's saved file. The student copy prints drafts, so this never runs the S4
export blocker gate; a document the renderer cannot render at all (for example
a declared picture without its stored payload) comes back as ``status="blocked"``
with a message instead of raising.
"""

from __future__ import annotations

import base64
from uuid import UUID

from skriptoteket.application.curated_apps.exam_workspace import (
    ExamWorkspacePrintPreviewResponse,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_document_store import (
    ExamWorkspaceDocumentStore,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_head_reader import (
    read_exam_workspace_working_state,
)
from skriptoteket.domain.curated_apps.exam_conversion.exam_print_house_template import (
    ExamPrintVariant,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_print_document import (
    build_print_document,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_print_html import (
    render_print_html,
)
from skriptoteket.domain.errors import DomainError
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.exam_workspace import (
    ExamPrintRendererProtocol,
    ExamWorkspaceContainerCodecProtocol,
)
from skriptoteket.protocols.vault import VaultFileRepositoryProtocol

_PNG_DATA_URL_PREFIX = "data:image/png;base64,"
_HEAD_CONFLICT_MESSAGE = "Det sparade provet har ändrats. Förhandsgranskningen uppdateras."


class PreviewExamWorkspacePrintHandler:
    """Render the requested retained history step into preview page images."""

    def __init__(
        self,
        *,
        vault_files: VaultFileRepositoryProtocol,
        codec: ExamWorkspaceContainerCodecProtocol,
        store: ExamWorkspaceDocumentStore,
        print_renderer: ExamPrintRendererProtocol,
    ) -> None:
        self._vault_files = vault_files
        self._codec = codec
        self._store = store
        self._print_renderer = print_renderer

    async def handle(
        self,
        *,
        actor: User,
        lineage_id: UUID,
        expected_revision: int,
        expected_cursor: UUID,
        step_id: UUID,
    ) -> ExamWorkspacePrintPreviewResponse:
        container = await read_exam_workspace_working_state(
            store=self._store,
            vault_files=self._vault_files,
            codec=self._codec,
            actor=actor,
            lineage_id=lineage_id,
            expected_revision=expected_revision,
            expected_cursor=expected_cursor,
            step_id=step_id,
            conflict_message=_HEAD_CONFLICT_MESSAGE,
        )
        document = container.document
        try:
            html = render_print_html(
                build_print_document(document, variant=ExamPrintVariant.STUDENT),
                assets=document.assets,
                assets_by_id=container.assets_by_id,
            )
        except DomainError as error:
            return ExamWorkspacePrintPreviewResponse(
                revision=document.revision,
                status="blocked",
                pages=[],
                question_pages={},
                message=error.message,
            )
        preview = await self._print_renderer.render_preview(html=html)
        return ExamWorkspacePrintPreviewResponse(
            revision=document.revision,
            status="ready",
            pages=[
                f"{_PNG_DATA_URL_PREFIX}{base64.b64encode(page).decode('ascii')}"
                for page in preview.pages
            ],
            question_pages=dict(preview.question_pages),
            message=None,
        )
