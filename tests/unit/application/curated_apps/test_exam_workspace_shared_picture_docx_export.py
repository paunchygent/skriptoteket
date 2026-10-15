"""DOCX export of the accepted shared-picture document through the real handler path (F7).

The teacher's DOCX export must keep the shared diagram: the export handler passes the saved
container's picture payloads to the writer, which embeds each one at its place in the
instruction. This walks the real export handler, document store, container codec and writer
over in-memory vault ports with a synthetic shared-picture fixture and stored payloads; it
is not host or browser proof.
"""

import io

import pytest
from docx import Document

from skriptoteket.application.curated_apps.exam_workspace import (
    ExamWorkspaceExportTarget,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_exports import (
    ExportExamWorkspaceDocumentHandler,
)
from skriptoteket.domain.curated_apps.exam_workspace.container import (
    ExamWorkspaceContainerContent,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_language_labels import (
    exam_language_labels,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_writer import (  # noqa: E501
    ExamWorkspaceDocxWriter,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_pdf_renderer import (
    WeasyPrintExamNetPdfRenderer,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_qti_writer import (
    ExamNetQtiPackageWriter,
)
from tests.unit.application.curated_apps.handlers.test_exam_workspace_documents import (
    _actor,
    _Env,
)
from tests.unit.infrastructure.curated_apps.test_exam_workspace_docx_writer import (
    _drawing_payload,
    _only_paragraph,
    shared_picture_document,
)


def _instruction_text(body: tuple[NativeParagraph, ...]) -> str:
    return "".join(
        segment.text
        for paragraph in body
        for segment in paragraph.segments
        if isinstance(segment, NativeTextSegment)
    )


@pytest.mark.asyncio
async def test_docx_export_embeds_shared_instruction_pictures_from_stored_payloads() -> None:
    fixture = shared_picture_document()
    env = _Env()
    actor = _actor()
    stored = await env.store.save_version(
        actor=actor,
        file_id=env.ids.new_uuid(),
        name="diagramprov.provdokument.zip",
        content=env.codec.build(
            content=ExamWorkspaceContainerContent(
                document=fixture.document,
                assets_by_id=fixture.assets_by_id,
                notes=(),
            )
        ),
        lineage_id=fixture.document.document_id,
        version=1,
    )
    lineage_id = stored.document_lineage_id
    assert lineage_id is not None
    handler = ExportExamWorkspaceDocumentHandler(
        vault_files=env.vault_files,
        codec=env.codec,
        store=env.store,
        qti_writer=ExamNetQtiPackageWriter(),
        pdf_renderer=WeasyPrintExamNetPdfRenderer(),
        docx_writer=ExamWorkspaceDocxWriter(),
    )

    result = await handler.handle(
        actor=actor,
        lineage_id=lineage_id,
        target=ExamWorkspaceExportTarget.DOCX,
        expected_revision=fixture.document.revision,
    )

    assert result.filename == "diagramprov.docx"
    assert result.media_type.endswith("wordprocessingml.document")
    parsed = Document(io.BytesIO(result.content))
    paragraphs = list(parsed.paragraphs)
    texts = [paragraph.text for paragraph in paragraphs]

    global_text = _instruction_text(fixture.document.instructions)
    assert (
        _drawing_payload(parsed, _only_paragraph(paragraphs, global_text))
        == fixture.assets_by_id[fixture.global_asset_id]
    )

    parent_text = _instruction_text(fixture.document.parents[0].instruction)
    assert (
        _drawing_payload(parsed, _only_paragraph(paragraphs, parent_text))
        == fixture.assets_by_id[fixture.parent_asset_id]
    )
    assert texts.count(parent_text) == 1

    labels = exam_language_labels(fixture.document)
    criterion = next(criterion for item in fixture.document.items for criterion in item.criteria)
    label_text = f"{labels.marking_guide}:"
    assert label_text in texts
    assert texts[texts.index(label_text) + 1] == f"• {criterion.text} ({criterion.points} p)"
    assert labels.answer_key in [
        paragraph.text
        for paragraph in paragraphs
        if paragraph.style is not None and paragraph.style.name == "Heading 2"
    ]
