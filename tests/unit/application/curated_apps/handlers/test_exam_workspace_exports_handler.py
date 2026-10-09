"""Unit tests for the exam workspace export handler (S4 gate + three targets)."""

from pathlib import Path
from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.exam_workspace import (
    SaveExamWorkspaceDocumentRequest,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_exports import (
    ExamWorkspaceExportTarget,
    ExportExamWorkspaceDocumentHandler,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
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
    imported = await env.import_handler.handle(
        actor=actor, filename=_FIXTURE.name, content=fixture_bytes
    )
    reviewed = _reviewed(imported.document).with_revision(2)
    await env.save_handler.handle(
        actor=actor,
        lineage_id=imported.summary.lineage_id,
        request=SaveExamWorkspaceDocumentRequest(expected_revision=1, document=reviewed),
    )
    return actor, imported.summary.lineage_id


@pytest.mark.asyncio
async def test_unreviewed_document_blocks_every_target(env: _Env, fixture_bytes: bytes) -> None:
    actor = _actor()
    imported = await env.import_handler.handle(
        actor=actor, filename=_FIXTURE.name, content=fixture_bytes
    )
    handler = _export_handler(env)
    for target in ExamWorkspaceExportTarget:
        with pytest.raises(DomainError) as exc_info:
            await handler.handle(actor=actor, lineage_id=imported.summary.lineage_id, target=target)
        assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
        assert "blockers" in (exc_info.value.details or {})


@pytest.mark.asyncio
async def test_qti_export_returns_zip_package(env: _Env, fixture_bytes: bytes) -> None:
    actor, lineage_id = await _imported_and_reviewed(env, fixture_bytes)
    result = await _export_handler(env).handle(
        actor=actor, lineage_id=lineage_id, target=ExamWorkspaceExportTarget.QTI
    )
    assert result.filename.endswith("-qti.zip")
    assert result.media_type == "application/zip"
    assert result.content.startswith(b"PK")


@pytest.mark.asyncio
async def test_pdf_export_returns_pdf(env: _Env, fixture_bytes: bytes) -> None:
    actor, lineage_id = await _imported_and_reviewed(env, fixture_bytes)
    result = await _export_handler(env).handle(
        actor=actor, lineage_id=lineage_id, target=ExamWorkspaceExportTarget.PDF
    )
    assert result.filename.endswith("-examnet.pdf")
    assert result.content.startswith(b"%PDF")


@pytest.mark.asyncio
async def test_docx_export_returns_validated_docx(env: _Env, fixture_bytes: bytes) -> None:
    actor, lineage_id = await _imported_and_reviewed(env, fixture_bytes)
    result = await _export_handler(env).handle(
        actor=actor, lineage_id=lineage_id, target=ExamWorkspaceExportTarget.DOCX
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
        )
    assert exc_info.value.code is ErrorCode.NOT_FOUND
