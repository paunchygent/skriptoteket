"""Rendering for native exam workspace exports (QTI/PDF/DOCX) and the import checklist.

Purpose:
  Render one already-loaded exam document with exactly the writers the signed-in
  export uses, so stateless public guest routes and saved-document routes share
  one export gate and one output shape.

Relationships:
  - Called by ``ExportExamWorkspaceDocumentHandler`` after it loads the saved head.
  - Called by ``PublicExamWorkspaceExportHandler`` with guest-supplied bytes.
  - Delegates to the fail-closed QTI, Exam.net PDF, house-template DOCX and
    print writers; the student and facit print PDFs render the
    house-template print HTML (W1) through the print renderer.
"""

from __future__ import annotations

from collections.abc import Mapping

from skriptoteket.application.curated_apps.exam_workspace import (
    ExamWorkspaceExportChecklistAllOrNothing,
    ExamWorkspaceExportChecklistCriterion,
    ExamWorkspaceExportChecklistEntry,
    ExamWorkspaceExportChecklistFreeTextCriteria,
    ExamWorkspaceExportChecklistResponse,
    ExamWorkspaceExportChecklistRoundedGaps,
    ExamWorkspaceExportFile,
    ExamWorkspaceExportTarget,
)
from skriptoteket.application.curated_apps.exam_workspace_exports import (
    build_native_examnet_qti_package,
    export_file_base_name,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_examnet_pdf_contracts import (
    DigiExamExamNetPdfStatus,
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
from skriptoteket.domain.curated_apps.exam_workspace.examnet_export_checklist import (
    ExamNetExportChecklistAllOrNothing,
    ExamNetExportChecklistEntry,
    ExamNetExportChecklistFreeTextCriteria,
    ExamNetExportChecklistRoundedGaps,
    native_exam_export_checklist,
)
from skriptoteket.domain.curated_apps.exam_workspace.examnet_pdf_export import (
    native_exam_to_pdf_document,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_export_rules import (
    INLINE_CHOICE_MIN_OPTIONS,
    native_export_blockers,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_list_labels import (
    native_exam_question_labels,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.protocols.exam_conversion import (
    ExamNetPdfRendererProtocol,
    ExamNetQtiPackageWriterProtocol,
)
from skriptoteket.protocols.exam_workspace import (
    ExamPrintRendererProtocol,
    ExamWorkspaceDocxWriterProtocol,
)

_DOCX_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


class ExamWorkspaceExportRenderer:
    """Turn one validated native exam document into an export file or checklist."""

    def __init__(
        self,
        *,
        qti_writer: ExamNetQtiPackageWriterProtocol,
        pdf_renderer: ExamNetPdfRendererProtocol,
        docx_writer: ExamWorkspaceDocxWriterProtocol,
        print_renderer: ExamPrintRendererProtocol,
    ) -> None:
        self._qti_writer = qti_writer
        self._pdf_renderer = pdf_renderer
        self._docx_writer = docx_writer
        self._print_renderer = print_renderer

    def render(
        self,
        *,
        document: NativeExamDocument,
        assets_by_id: Mapping[str, bytes],
        target: ExamWorkspaceExportTarget,
    ) -> ExamWorkspaceExportFile:
        self._raise_for_blockers(document)

        base = export_file_base_name(document)
        if target is ExamWorkspaceExportTarget.QTI:
            package_bytes, _report_bytes = build_native_examnet_qti_package(
                document,
                package_name=base,
                qti_writer=self._qti_writer,
                assets_by_id=assets_by_id,
            )
            return ExamWorkspaceExportFile(
                filename=f"{base}.zip",
                media_type="application/zip",
                content=package_bytes,
            )
        if target is ExamWorkspaceExportTarget.PDF:
            return self._print_pdf(
                document=document,
                assets_by_id=assets_by_id,
                variant=ExamPrintVariant.STUDENT,
                filename=f"{base}.pdf",
            )
        if target is ExamWorkspaceExportTarget.PDF_FACIT:
            return self._print_pdf(
                document=document,
                assets_by_id=assets_by_id,
                variant=ExamPrintVariant.FACIT,
                filename=f"{base} facit.pdf",
            )
        if target is ExamWorkspaceExportTarget.EXAMNET_PDF:
            pdf_document = native_exam_to_pdf_document(document, assets_by_id=assets_by_id)
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
                filename=f"{base} Exam.net.pdf",
                media_type="application/pdf",
                content=self._pdf_renderer.render_pdf(document=pdf_document),
            )

        content = self._docx_writer.build_docx_bytes(document, assets_by_id=assets_by_id)
        self._docx_writer.validate_docx_bytes(content, expected_item_count=len(document.items))
        return ExamWorkspaceExportFile(
            filename=f"{base}.docx",
            media_type=_DOCX_MEDIA_TYPE,
            content=content,
        )

    def _print_pdf(
        self,
        *,
        document: NativeExamDocument,
        assets_by_id: Mapping[str, bytes],
        variant: ExamPrintVariant,
        filename: str,
    ) -> ExamWorkspaceExportFile:
        """Render one print-PDF variant from the house-template HTML (W1)."""
        html = render_print_html(
            build_print_document(document, variant=variant),
            assets=document.assets,
            assets_by_id=assets_by_id,
        )
        return ExamWorkspaceExportFile(
            filename=filename,
            media_type="application/pdf",
            content=self._print_renderer.render_pdf(html=html),
        )

    def checklist(
        self,
        *,
        document: NativeExamDocument,
        assets_by_id: Mapping[str, bytes],
    ) -> ExamWorkspaceExportChecklistResponse:
        self._raise_for_blockers(document)
        entries = native_exam_export_checklist(document, assets_by_id=assets_by_id)
        return ExamWorkspaceExportChecklistResponse(
            entries=tuple(_checklist_entry(entry) for entry in entries),
            inline_choice_min_options=INLINE_CHOICE_MIN_OPTIONS,
        )

    def _raise_for_blockers(self, document: NativeExamDocument) -> None:
        blockers = native_export_blockers(document)
        if blockers:
            heading_items = {
                blocker.item_id
                for blocker in blockers
                if blocker.reason == "inline_choice_option_heading"
            }
            labels = native_exam_question_labels(document)
            heading_messages = [
                f"Fråga {labels[item.item_id]}: Rubrikformat är inte tillåtet i rullistealternativ."
                for item in document.items
                if item.item_id in heading_items
            ]
            title_messages = [
                "Ge provet en titel med bokstäver eller siffror."
                for blocker in blockers
                if blocker.reason == "title_without_text"
            ]
            has_item_blockers = any(blocker.item_id is not None for blocker in blockers)
            message = " ".join(
                [
                    *(
                        ["Provet har frågor som måste åtgärdas före export."]
                        if has_item_blockers
                        else []
                    ),
                    *title_messages,
                    *heading_messages,
                ]
            )
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message=message,
                details={"blockers": [blocker.model_dump(mode="json") for blocker in blockers]},
            )


def _checklist_entry(entry: ExamNetExportChecklistEntry) -> ExamWorkspaceExportChecklistEntry:
    """Map one domain checklist entry onto the wire shape the export panel reads."""

    if isinstance(entry, ExamNetExportChecklistFreeTextCriteria):
        return ExamWorkspaceExportChecklistFreeTextCriteria(
            kind="free_text_criteria",
            item_id=entry.item_id,
            question_text=entry.question_text,
            points=entry.points,
            criteria=tuple(
                ExamWorkspaceExportChecklistCriterion(text=criterion.text, points=criterion.points)
                for criterion in entry.criteria
            ),
        )
    if isinstance(entry, ExamNetExportChecklistAllOrNothing):
        return ExamWorkspaceExportChecklistAllOrNothing(
            kind="all_or_nothing",
            item_id=entry.item_id,
            question_text=entry.question_text,
            points=entry.points,
        )
    if isinstance(entry, ExamNetExportChecklistRoundedGaps):
        return ExamWorkspaceExportChecklistRoundedGaps(
            kind="rounded_gaps",
            item_id=entry.item_id,
            question_text=entry.question_text,
            points=entry.points,
            gap_points=entry.gap_points,
        )
    raise TypeError(f"Unknown checklist entry: {entry!r}")
