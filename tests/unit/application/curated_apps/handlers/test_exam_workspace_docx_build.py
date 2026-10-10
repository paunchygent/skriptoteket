"""Whole-exam build replayed from the recorded live provider rounds."""

import io
import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.exam_workspace_exports import (
    build_native_examnet_qti_package,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build import DocxAIConverter
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    AnswerKeyProviderRoute,
    StructuredLLMEndpointKind,
    StructuredLLMProviderProfile,
    StructuredLLMResponse,
    StructuredLLMUsage,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_token_lease import (
    AnswerKeyTokenLease,
    AnswerKeyTokenLeaseState,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeItemReviewState,
    native_export_blockers,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub import (
    exam_workspace_docx_chunker,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.examnet_qti_writer import (
    ExamNetQtiPackageWriter,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.exam_answer_key import (
    AnswerKeyProviderSelectorProtocol,
    AnswerKeyStructuredProviderProtocol,
    AnswerKeyTokenLeaseRepositoryProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

_NOW = datetime(2026, 10, 10, 18, tzinfo=UTC)


def ports():
    provider = AsyncMock(spec=AnswerKeyStructuredProviderProtocol)
    leases = AsyncMock(spec=AnswerKeyTokenLeaseRepositoryProtocol)
    leases.reserve.return_value = AnswerKeyTokenLease(
        lease_id=uuid4(),
        utc_day=_NOW.date(),
        reserved_tokens=20000,
        state=AnswerKeyTokenLeaseState.RESERVED,
    )
    uow = AsyncMock(spec=UnitOfWorkProtocol)
    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = _NOW
    primary = StructuredLLMProviderProfile(
        "primary", "model", StructuredLLMEndpointKind.RESPONSES, True, 128000, 4096
    )
    backup = StructuredLLMProviderProfile(
        "backup", "other", StructuredLLMEndpointKind.CHAT_COMPLETIONS, True, 128000, 4096
    )
    selector = Mock(spec=AnswerKeyProviderSelectorProtocol)
    selector.select_route.return_value = AnswerKeyProviderRoute(primary, backup)
    converter = DocxAIConverter(provider, selector, leases, uow, clock, True)
    return converter, provider


async def test_recorded_quiz_one_round_builds_all_items_and_exports_qti():
    fixture = Path("tests/fixtures/exam_conversion")
    chunks = exam_workspace_docx_chunker.PythonDocxExamChunker().chunk(
        content=(
            fixture / "docx_corpus/chapter_4_poetry_and_lyrics_quiz_med_facit.docx"
        ).read_bytes()
    )
    converter, provider = ports()
    provider.complete_structured.return_value = StructuredLLMResponse(
        json.loads((fixture / "chapter_4_poetry_docx_build_response.json").read_text()),
        "completed",
        StructuredLLMUsage(),
    )
    result = await converter.convert(
        job_id=uuid4(),
        document_id=uuid4(),
        filename="test.docx",
        source_sha256="a" * 64,
        chunks=chunks,
    )
    assert provider.complete_structured.await_count == 1
    assert result.document.title == "Chapter 4: Poetry and Lyrics — Vocabulary and Terminology Quiz"
    assert len(result.document.items) == 28
    assert sum(item.points for item in result.document.items) == 28
    assert [item.kind.value for item in result.document.items] == ["single_choice"] * 21 + [
        "gap_fill"
    ] * 7
    assert all(
        i.review.state is NativeItemReviewState.REVIEW_COMPLETE for i in result.document.items
    )
    assert result.events == ()
    assert native_export_blockers(result.document) == ()
    package, report = build_native_examnet_qti_package(
        result.document, package_name="probe", qti_writer=ExamNetQtiPackageWriter()
    )
    assert json.loads(report)["package_status"] == "passed"
    with zipfile.ZipFile(io.BytesIO(package)) as archive:
        assert "imsmanifest.xml" in archive.namelist()
