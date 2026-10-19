"""Unit tests for the exam workspace export handler (S4 gate + three targets)."""

from io import BytesIO
from pathlib import Path
from uuid import UUID, uuid4
from xml.etree import ElementTree
from zipfile import ZipFile

import pytest

from skriptoteket.application.curated_apps.exam_workspace import (
    ExamWorkspaceExportChecklistCriterion,
    ExamWorkspaceExportChecklistFreeTextCriteria,
    ExamWorkspaceExportChecklistRoundedGaps,
    ExamWorkspaceExportTarget,
    SaveExamWorkspaceDocumentRequest,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_export_renderer import (
    ExamWorkspaceExportRenderer,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_exports import (
    ExportExamWorkspaceDocumentHandler,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_examnet_pdf_contracts import (
    DigiExamExamNetPdfDocument,
    DigiExamExamNetPdfStatus,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_criteria import (
    NativeExamCriterion,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_export_rules import (
    INLINE_CHOICE_MIN_OPTIONS,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
    NativeExamItem,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import User
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_writer import (  # noqa: E501
    ExamWorkspaceDocxWriter,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_pdf_renderer import (
    WeasyPrintExamNetPdfRenderer,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_qti_writer import (
    ExamNetQtiPackageWriter,
)
from skriptoteket.protocols.exam_conversion import ExamNetPdfRendererProtocol
from skriptoteket.protocols.exam_workspace import (
    ExamPrintPreviewPages,
    ExamPrintRendererProtocol,
)
from tests.unit.application.curated_apps.handlers.test_exam_workspace_documents import (
    _actor,
    _Env,
)
from tests.unit.application.curated_apps.test_exam_workspace_exports import (
    _reviewed,
    _source_fallback_document,
)
from tests.unit.domain.curated_apps.exam_workspace.inline_choice_test_support import (
    inline_choice_item,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_document_test_support import (
    with_next_revision,
)

_FIXTURE = Path(
    "tests/fixtures/exam_conversion/real_inputs/grammatik_omprov_examnet_import_med_facit.docx"
)


class _FakePrintRenderer:
    """Record the print HTML the handler built and return a marker PDF."""

    def __init__(self) -> None:
        self.html_by_call: list[str] = []

    def render_pdf(self, *, html: str) -> bytes:
        self.html_by_call.append(html)
        return b"%PDF-print"

    async def render_preview(self, *, html: str) -> ExamPrintPreviewPages:
        raise AssertionError("the export handler never renders previews")


class _FakeExamNetPdfRenderer:
    """Record the import-plan documents the Exam.net PDF branch renders."""

    def __init__(self) -> None:
        self.documents: list[DigiExamExamNetPdfDocument] = []

    def render_pdf(self, *, document: DigiExamExamNetPdfDocument) -> bytes:
        self.documents.append(document)
        return b"%PDF-examnet"


def _export_handler(
    env: _Env,
    *,
    print_renderer: ExamPrintRendererProtocol | None = None,
    pdf_renderer: ExamNetPdfRendererProtocol | None = None,
) -> ExportExamWorkspaceDocumentHandler:
    return ExportExamWorkspaceDocumentHandler(
        vault_files=env.vault_files,
        codec=env.codec,
        store=env.store,
        renderer=ExamWorkspaceExportRenderer(
            qti_writer=ExamNetQtiPackageWriter(),
            pdf_renderer=pdf_renderer
            if pdf_renderer is not None
            else WeasyPrintExamNetPdfRenderer(),
            docx_writer=ExamWorkspaceDocxWriter(),
            print_renderer=(print_renderer if print_renderer is not None else _FakePrintRenderer()),
        ),
    )


@pytest.fixture()
def env() -> _Env:
    return _Env()


@pytest.fixture(scope="module")
def fixture_bytes() -> bytes:
    return _FIXTURE.read_bytes()


async def _imported_and_reviewed(env: _Env, fixture_bytes: bytes):
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    reviewed = with_next_revision(_reviewed(imported.document))
    await env.save_handler.handle(
        actor=actor,
        lineage_id=imported.summary.lineage_id,
        request=SaveExamWorkspaceDocumentRequest(
            expected_revision=1, document=reviewed, position_step_id=imported.summary.lineage_id
        ),
    )
    return actor, imported.summary.lineage_id


def _loss_item(item: NativeExamItem) -> NativeExamItem:
    """Give the seeded fixture one rounded Lucktext and one Fritext with criteria."""

    if item.item_id == "item_001":
        # The fixture's 6 points over 3 gaps divide evenly; 5 leaves 1.66 per gap.
        return item.model_copy(update={"points": 5})
    if item.kind is NativeExamItemKind.FREE_TEXT:
        points = int(item.points or 1)
        return item.model_copy(
            update={
                "points": points,
                "criteria": (NativeExamCriterion(text="Ett korrekt resonemang.", points=points),),
            }
        )
    return item


async def _imported_and_reviewed_with_losses(env: _Env) -> tuple[User, UUID]:
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    reviewed = _reviewed(imported.document)
    document = with_next_revision(
        reviewed.model_copy(update={"items": tuple(_loss_item(item) for item in reviewed.items)})
    )
    await env.save_handler.handle(
        actor=actor,
        lineage_id=imported.summary.lineage_id,
        request=SaveExamWorkspaceDocumentRequest(
            expected_revision=1, document=document, position_step_id=imported.summary.lineage_id
        ),
    )
    return actor, imported.summary.lineage_id


@pytest.mark.asyncio
async def test_source_fallback_blocks_every_target(env: _Env) -> None:
    actor = _actor()
    imported = await env.seed_document(actor=actor, document=_source_fallback_document())
    handler = _export_handler(env)
    for target in ExamWorkspaceExportTarget:
        with pytest.raises(DomainError) as exc_info:
            await handler.handle(
                actor=actor,
                lineage_id=imported.summary.lineage_id,
                target=target,
                expected_revision=1,
            )
        assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
        assert "blockers" in (exc_info.value.details or {})


@pytest.mark.asyncio
@pytest.mark.parametrize("operation", ["export", "checklist"])
async def test_heading_dropdown_refuses_export_and_checklist_with_question_number(
    env: _Env, operation: str
) -> None:
    actor = _actor()
    imported = await env.seed_document(actor=actor)
    item_payload = inline_choice_item(sequence=2, points=2).model_dump(mode="json")
    item_payload["gaps"][0]["options"][0]["body"][0]["heading_level"] = 2
    item = NativeExamItem.model_validate(item_payload)
    document = with_next_revision(
        imported.document.model_copy(update={"items": (inline_choice_item(points=2), item)})
    )
    await env.save_handler.handle(
        actor=actor,
        lineage_id=imported.summary.lineage_id,
        request=SaveExamWorkspaceDocumentRequest(
            expected_revision=1, document=document, position_step_id=imported.summary.lineage_id
        ),
    )
    handler = _export_handler(env)
    with pytest.raises(DomainError) as exc_info:
        if operation == "export":
            await handler.handle(
                actor=actor,
                lineage_id=imported.summary.lineage_id,
                target=ExamWorkspaceExportTarget.QTI,
                expected_revision=2,
            )
        else:
            await handler.checklist(
                actor=actor, lineage_id=imported.summary.lineage_id, expected_revision=2
            )
    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert "Fråga 2: Rubrikformat är inte tillåtet i rullistealternativ." in exc_info.value.message
    assert exc_info.value.details == {
        "blockers": [{"item_id": "item_002", "reason": "inline_choice_option_heading"}],
    }


@pytest.mark.asyncio
async def test_qti_export_returns_zip_package(env: _Env, fixture_bytes: bytes) -> None:
    actor, lineage_id = await _imported_and_reviewed(env, fixture_bytes)
    result = await _export_handler(env).handle(
        actor=actor,
        lineage_id=lineage_id,
        target=ExamWorkspaceExportTarget.QTI,
        expected_revision=2,
    )
    assert result.filename == "Omprov grammatik och språkstrukturer.zip"
    assert result.media_type == "application/zip"
    assert result.content.startswith(b"PK")


@pytest.mark.asyncio
async def test_student_pdf_export_renders_the_student_print_html(
    env: _Env, fixture_bytes: bytes
) -> None:
    actor, lineage_id = await _imported_and_reviewed(env, fixture_bytes)
    print_renderer = _FakePrintRenderer()
    result = await _export_handler(env, print_renderer=print_renderer).handle(
        actor=actor,
        lineage_id=lineage_id,
        target=ExamWorkspaceExportTarget.PDF,
        expected_revision=2,
    )
    assert result.filename == "Omprov grammatik och språkstrukturer.pdf"
    assert result.media_type == "application/pdf"
    assert result.content == b"%PDF-print"
    assert len(print_renderer.html_by_call) == 1
    assert "– Elevexemplar</title>" in print_renderer.html_by_call[0]
    assert "– Facit</title>" not in print_renderer.html_by_call[0]


@pytest.mark.asyncio
async def test_facit_pdf_export_renders_the_facit_print_html(
    env: _Env, fixture_bytes: bytes
) -> None:
    actor, lineage_id = await _imported_and_reviewed(env, fixture_bytes)
    print_renderer = _FakePrintRenderer()
    result = await _export_handler(env, print_renderer=print_renderer).handle(
        actor=actor,
        lineage_id=lineage_id,
        target=ExamWorkspaceExportTarget.PDF_FACIT,
        expected_revision=2,
    )
    assert result.filename == "Omprov grammatik och språkstrukturer facit.pdf"
    assert result.media_type == "application/pdf"
    assert result.content == b"%PDF-print"
    assert len(print_renderer.html_by_call) == 1
    assert "– Facit</title>" in print_renderer.html_by_call[0]
    assert "– Elevexemplar</title>" not in print_renderer.html_by_call[0]


@pytest.mark.asyncio
async def test_examnet_pdf_export_renders_the_import_plan_document(
    env: _Env, fixture_bytes: bytes
) -> None:
    actor, lineage_id = await _imported_and_reviewed(env, fixture_bytes)
    pdf_renderer = _FakeExamNetPdfRenderer()
    print_renderer = _FakePrintRenderer()
    result = await _export_handler(
        env, pdf_renderer=pdf_renderer, print_renderer=print_renderer
    ).handle(
        actor=actor,
        lineage_id=lineage_id,
        target=ExamWorkspaceExportTarget.EXAMNET_PDF,
        expected_revision=2,
    )
    assert result.filename == "Omprov grammatik och språkstrukturer Exam.net.pdf"
    assert result.media_type == "application/pdf"
    assert result.content == b"%PDF-examnet"
    assert len(pdf_renderer.documents) == 1
    assert pdf_renderer.documents[0].status is DigiExamExamNetPdfStatus.SUCCESS
    assert print_renderer.html_by_call == []


@pytest.mark.asyncio
async def test_docx_export_returns_validated_docx(env: _Env, fixture_bytes: bytes) -> None:
    actor, lineage_id = await _imported_and_reviewed(env, fixture_bytes)
    result = await _export_handler(env).handle(
        actor=actor,
        lineage_id=lineage_id,
        target=ExamWorkspaceExportTarget.DOCX,
        expected_revision=2,
    )
    assert result.filename == "Omprov grammatik och språkstrukturer.docx"
    assert result.content.startswith(b"PK")


@pytest.mark.asyncio
async def test_unknown_lineage_is_not_found(env: _Env) -> None:
    with pytest.raises(DomainError) as exc_info:
        await _export_handler(env).handle(
            actor=_actor(),
            lineage_id=uuid4(),
            target=ExamWorkspaceExportTarget.QTI,
            expected_revision=1,
        )
    assert exc_info.value.code is ErrorCode.NOT_FOUND


@pytest.mark.asyncio
async def test_intervening_save_refuses_checklist_for_the_downloaded_revision(env: _Env) -> None:
    actor, lineage_id = await _imported_and_reviewed_with_losses(env)
    handler = _export_handler(env)
    downloaded = await handler.handle(
        actor=actor,
        lineage_id=lineage_id,
        target=ExamWorkspaceExportTarget.QTI,
        expected_revision=2,
    )
    head = await env.vault_files.get_document_head(user_id=actor.id, document_lineage_id=lineage_id)
    assert head is not None
    current = env.codec.parse(content=await env.store.load(actor=actor, vault_file=head)).document
    changed = with_next_revision(
        current.model_copy(
            update={
                "items": tuple(
                    item.model_copy(update={"points": 6})
                    if item.item_id == "item_001"
                    else item.model_copy(
                        update={
                            "points": 2,
                            "criteria": (
                                NativeExamCriterion(text="Changed in another tab", points=2),
                            ),
                        }
                    )
                    if item.criteria
                    else item
                    for item in current.items
                )
            }
        )
    )
    await env.save_handler.handle(
        actor=actor,
        lineage_id=lineage_id,
        request=SaveExamWorkspaceDocumentRequest(
            expected_revision=2,
            document=changed,
            position_step_id=(
                await env.save_handler.history(actor=actor, lineage_id=lineage_id)
            ).position_step_id,
        ),
    )
    with ZipFile(BytesIO(downloaded.content)) as package:
        roots = [
            ElementTree.fromstring(package.read(name))
            for name in package.namelist()
            if name.startswith("items/") and name.endswith(".xml")
        ]
    assert any(node.attrib.get("mapped-value") == "1.66" for root in roots for node in root.iter())
    with pytest.raises(DomainError) as exc_info:
        await handler.checklist(actor=actor, lineage_id=lineage_id, expected_revision=2)
    assert exc_info.value.code is ErrorCode.CONFLICT
    assert exc_info.value.details == {"expected_revision": 2, "current_revision": 3}
    newer = await handler.checklist(actor=actor, lineage_id=lineage_id, expected_revision=3)
    assert not any(entry.kind == "rounded_gaps" for entry in newer.entries)
    assert any(
        isinstance(entry, ExamWorkspaceExportChecklistFreeTextCriteria)
        and entry.criteria
        == (ExamWorkspaceExportChecklistCriterion(text="Changed in another tab", points=2),)
        for entry in newer.entries
    )
    with pytest.raises(DomainError) as stale_export:
        await handler.handle(
            actor=actor,
            lineage_id=lineage_id,
            target=ExamWorkspaceExportTarget.QTI,
            expected_revision=2,
        )
    assert stale_export.value.code is ErrorCode.CONFLICT


@pytest.mark.asyncio
async def test_checklist_lists_the_saved_heads_losses(env: _Env) -> None:
    actor, lineage_id = await _imported_and_reviewed_with_losses(env)

    response = await _export_handler(env).checklist(
        actor=actor, lineage_id=lineage_id, expected_revision=2
    )

    assert response.inline_choice_min_options == INLINE_CHOICE_MIN_OPTIONS
    entries = response.entries
    assert len(entries) == 2
    rounded, criteria = entries
    assert isinstance(rounded, ExamWorkspaceExportChecklistRoundedGaps)
    assert rounded.question_number == "1"
    assert rounded.points == 5
    assert rounded.gap_points == 1.66
    assert rounded.question_text
    assert isinstance(criteria, ExamWorkspaceExportChecklistFreeTextCriteria)
    assert criteria.question_number == "8"
    assert criteria.points == 8
    assert criteria.criteria == (
        ExamWorkspaceExportChecklistCriterion(text="Ett korrekt resonemang.", points=8),
    )
    assert criteria.question_text


@pytest.mark.asyncio
async def test_source_fallback_blocks_the_checklist(env: _Env) -> None:
    actor = _actor()
    imported = await env.seed_document(actor=actor, document=_source_fallback_document())

    with pytest.raises(DomainError) as exc_info:
        await _export_handler(env).checklist(
            actor=actor, lineage_id=imported.summary.lineage_id, expected_revision=1
        )

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert "blockers" in (exc_info.value.details or {})


@pytest.mark.asyncio
async def test_checklist_unknown_lineage_is_not_found(env: _Env) -> None:
    with pytest.raises(DomainError) as exc_info:
        await _export_handler(env).checklist(
            actor=_actor(), lineage_id=uuid4(), expected_revision=1
        )
    assert exc_info.value.code is ErrorCode.NOT_FOUND
