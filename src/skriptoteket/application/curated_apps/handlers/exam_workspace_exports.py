"""On-demand exports for native exam workspace documents (D3/S4).

Every target runs the S4 export gate first: items needing review or
carrying unreviewed machine-proposed keys block QTI, PDF, and DOCX alike.
QTI and PDF ride the existing fail-closed writers and validators; DOCX
goes through the minimal validated writer.
"""

from __future__ import annotations

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from skriptoteket.application.curated_apps.exam_workspace_exports import (
    build_native_examnet_qti_package,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_documents import (
    ExamWorkspaceDocumentStore,
    _document_not_found,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_examnet_pdf_contracts import (
    DigiExamExamNetPdfStatus,
)
from skriptoteket.domain.curated_apps.exam_workspace.container import (
    ExamWorkspaceContainerContent,
)
from skriptoteket.domain.curated_apps.exam_workspace.examnet_pdf_export import (
    native_exam_to_pdf_document,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    native_export_blockers,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.vault import VaultFile
from skriptoteket.protocols.exam_conversion import (
    ExamNetPdfRendererProtocol,
    ExamNetQtiPackageWriterProtocol,
)
from skriptoteket.protocols.exam_workspace import (
    ExamWorkspaceContainerCodecProtocol,
    ExamWorkspaceDocxWriterProtocol,
)
from skriptoteket.protocols.vault import VaultFileRepositoryProtocol

_DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
_CONTAINER_SUFFIX = ".provdokument.zip"


class ExamWorkspaceExportTarget(StrEnum):
    QTI = "qti"
    PDF = "pdf"
    DOCX = "docx"


class ExamWorkspaceExportFile(BaseModel):
    model_config = ConfigDict(frozen=True)

    filename: str
    media_type: str
    content: bytes


class ExportExamWorkspaceDocumentHandler:
    """Generate one validated export file from the head document revision."""

    def __init__(
        self,
        *,
        vault_files: VaultFileRepositoryProtocol,
        codec: ExamWorkspaceContainerCodecProtocol,
        store: ExamWorkspaceDocumentStore,
        qti_writer: ExamNetQtiPackageWriterProtocol,
        pdf_renderer: ExamNetPdfRendererProtocol,
        docx_writer: ExamWorkspaceDocxWriterProtocol,
    ) -> None:
        self._vault_files = vault_files
        self._codec = codec
        self._store = store
        self._qti_writer = qti_writer
        self._pdf_renderer = pdf_renderer
        self._docx_writer = docx_writer

    async def handle(
        self,
        *,
        actor: User,
        lineage_id: UUID,
        target: ExamWorkspaceExportTarget,
    ) -> ExamWorkspaceExportFile:
        head, container = await self._load_head(actor=actor, lineage_id=lineage_id)
        document = container.document

        blockers = native_export_blockers(document)
        if blockers:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Provet har frågor som behöver granskas före export.",
                details={"blockers": [blocker.model_dump(mode="json") for blocker in blockers]},
            )

        base = head.name.removesuffix(_CONTAINER_SUFFIX) or "prov"
        if target is ExamWorkspaceExportTarget.QTI:
            package_bytes, _report_bytes = build_native_examnet_qti_package(
                document,
                package_name=base,
                qti_writer=self._qti_writer,
                assets_by_id=container.assets_by_id,
            )
            return ExamWorkspaceExportFile(
                filename=f"{base}-qti.zip",
                media_type="application/zip",
                content=package_bytes,
            )
        if target is ExamWorkspaceExportTarget.PDF:
            pdf_document = native_exam_to_pdf_document(
                document, assets_by_id=container.assets_by_id
            )
            if pdf_document.status is not DigiExamExamNetPdfStatus.SUCCESS:
                raise DomainError(
                    code=ErrorCode.VALIDATION_ERROR,
                    message="PDF-exporten blockerades av dokumentets innehåll.",
                    details={
                        "warnings": [
                            {
                                "code": warning.code.value,
                                "message": warning.message,
                                "item_id": warning.item_id,
                            }
                            for warning in pdf_document.warnings
                        ]
                    },
                )
            return ExamWorkspaceExportFile(
                filename=f"{base}-examnet.pdf",
                media_type="application/pdf",
                content=self._pdf_renderer.render_pdf(document=pdf_document),
            )

        content = self._docx_writer.build_docx_bytes(document)
        self._docx_writer.validate_docx_bytes(content, expected_item_count=len(document.items))
        return ExamWorkspaceExportFile(
            filename=f"{base}.docx",
            media_type=_DOCX_MEDIA_TYPE,
            content=content,
        )

    async def _load_head(
        self, *, actor: User, lineage_id: UUID
    ) -> tuple[VaultFile, ExamWorkspaceContainerContent]:
        head = await self._vault_files.get_document_head(
            user_id=actor.id, document_lineage_id=lineage_id
        )
        if head is None:
            raise _document_not_found(lineage_id)
        content = await self._store.load_version(actor=actor, vault_file=head)
        return head, self._codec.parse(content=content)
