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
from skriptoteket.application.curated_apps.handlers.exam_workspace_exports import (
    ExportExamWorkspaceDocumentHandler,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_criteria import (
    NativeExamCriterion,
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
from tests.unit.application.curated_apps.handlers.test_exam_workspace_documents import (
    _actor,
    _Env,
)
from tests.unit.application.curated_apps.test_exam_workspace_exports import _reviewed
from tests.unit.domain.curated_apps.exam_workspace.native_exam_document_test_support import (
    with_next_revision,
)

_FIXTURE = Path(
    "tests/fixtures/exam_conversion/real_inputs/grammatik_omprov_examnet_import_med_facit.docx"
)


def _export_handler(env: _Env) -> ExportExamWorkspaceDocumentHandler:
    return ExportExamWorkspaceDocumentHandler(
        vault_files=env.vault_files,
        codec=env.codec,
        store=env.store,
        qti_writer=ExamNetQtiPackageWriter(),
        pdf_renderer=WeasyPrintExamNetPdfRenderer(),
        docx_writer=ExamWorkspaceDocxWriter(),
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
        request=SaveExamWorkspaceDocumentRequest(expected_revision=1, document=reviewed),
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
        request=SaveExamWorkspaceDocumentRequest(expected_revision=1, document=document),
    )
    return actor, imported.summary.lineage_id


@pytest.mark.asyncio
async def test_unreviewed_document_blocks_every_target(env: _Env, fixture_bytes: bytes) -> None:
    actor = _actor()
    imported = await env.seed_document(actor=actor)
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
async def test_qti_export_returns_zip_package(env: _Env, fixture_bytes: bytes) -> None:
    actor, lineage_id = await _imported_and_reviewed(env, fixture_bytes)
    result = await _export_handler(env).handle(
        actor=actor,
        lineage_id=lineage_id,
        target=ExamWorkspaceExportTarget.QTI,
        expected_revision=2,
    )
    assert result.filename.endswith("-qti.zip")
    assert result.media_type == "application/zip"
    assert result.content.startswith(b"PK")


@pytest.mark.asyncio
async def test_pdf_export_returns_pdf(env: _Env, fixture_bytes: bytes) -> None:
    actor, lineage_id = await _imported_and_reviewed(env, fixture_bytes)
    result = await _export_handler(env).handle(
        actor=actor,
        lineage_id=lineage_id,
        target=ExamWorkspaceExportTarget.PDF,
        expected_revision=2,
    )
    assert result.filename.endswith("-examnet.pdf")
    assert result.content.startswith(b"%PDF")


@pytest.mark.asyncio
async def test_docx_export_returns_validated_docx(env: _Env, fixture_bytes: bytes) -> None:
    actor, lineage_id = await _imported_and_reviewed(env, fixture_bytes)
    result = await _export_handler(env).handle(
        actor=actor,
        lineage_id=lineage_id,
        target=ExamWorkspaceExportTarget.DOCX,
        expected_revision=2,
    )
    assert result.filename.endswith(".docx")
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
    current = env.codec.parse(
        content=await env.store.load_version(actor=actor, vault_file=head)
    ).document
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
        request=SaveExamWorkspaceDocumentRequest(expected_revision=2, document=changed),
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
async def test_unreviewed_document_blocks_the_checklist(env: _Env) -> None:
    actor = _actor()
    imported = await env.seed_document(actor=actor)

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
