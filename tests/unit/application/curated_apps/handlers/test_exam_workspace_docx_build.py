"""Whole-exam build replayed from the recorded live provider rounds."""

import io
import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from scripts.exam_conversion_eval.gold import GoldExam, GoldItem
from skriptoteket.application.curated_apps.exam_workspace_exports import (
    build_native_examnet_qti_package,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build import DocxAIConverter
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_rounds import (
    build_round_request,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMEndpointKind,
    StructuredLLMProviderProfile,
    StructuredLLMResponse,
    StructuredLLMUsage,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_token_lease import (
    AnswerKeyTokenLease,
    AnswerKeyTokenLeaseState,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import DocxBuildResult
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
    NativeItemReviewState,
    NativeTextSegment,
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
    converter = DocxAIConverter(provider, primary, leases, uow, clock, True)
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
    assert result.document.title == (
        "Chapter 4: Poetry and Lyrics — Vocabulary and Terminology Quiz — answer key"
    )
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


_FIXTURES = Path("tests/fixtures/exam_conversion")


def _recorded(name: str) -> StructuredLLMResponse:
    return StructuredLLMResponse(
        json.loads((_FIXTURES / name).read_text()), "completed", StructuredLLMUsage()
    )


async def _replay(exam: str, *responses: str) -> tuple[DocxBuildResult, list[DocxChunk]]:
    chunks = exam_workspace_docx_chunker.PythonDocxExamChunker().chunk(
        content=(_FIXTURES / f"docx_corpus/{exam}.docx").read_bytes()
    )
    converter, provider = ports()
    provider.complete_structured.side_effect = [_recorded(name) for name in responses]
    result = await converter.convert(
        job_id=uuid4(),
        document_id=uuid4(),
        filename=f"{exam}.docx",
        source_sha256="a" * 64,
        chunks=chunks,
    )
    assert provider.complete_structured.await_count == len(responses)
    return result, list(chunks)


def _student_texts(document: NativeExamDocument) -> list[str]:
    texts = [document.title, *document.instructions]
    for item in document.items:
        texts.extend(t for t in (item.title,) if t)
        texts.extend(
            segment.text
            for paragraph in item.body
            for segment in paragraph.segments
            if isinstance(segment, NativeTextSegment)
        )
        texts.extend(choice.text for choice in item.choices)
        texts.extend(gap.hint for gap in item.gaps if gap.hint)
    return [" ".join(text.split()) for text in texts]


def _gold(exam: str) -> tuple[GoldItem, ...]:
    path = _FIXTURES / f"docx_corpus/gold/{exam}.json"
    items: tuple[GoldItem, ...] = GoldExam.model_validate_json(path.read_bytes()).items
    return items


def _inline_facit(exam: str) -> set[str]:
    """Gold blank preceded by its source word, filled with the gold answer: 'lek R'."""
    leaks: set[str] = set()
    for item in _gold(exam):
        parts = item.prompt.split("[___]")
        for before, gap in zip(parts, item.gaps, strict=False):
            words = before.split()
            if words:
                leaks.update(f"{words[-1]} {value}" for value in gap.accepted_values)
    return leaks


def _assert_no_facit(
    result: DocxBuildResult, chunks: list[DocxChunk], exam: str, *responses: str
) -> None:
    """Neither the model's answer-key chunks nor gold inline answers reach student text."""
    key_anchors = {
        anchor
        for name in responses
        for anchor in json.loads((_FIXTURES / name).read_text())["answer_key_anchors"]
    }
    key_texts = {" ".join(c.text.split()) for c in chunks if c.anchor in key_anchors}
    student = _student_texts(result.document)
    leaked = sorted(
        {fact for fact in key_texts | _inline_facit(exam) for text in student if fact in text}
    )
    assert key_texts
    assert leaked == []


_ENGLISH = "bf26_english_1_unit_test_kap_1_2_med_facit"


def _assert_review_events_carry_reasons(result: DocxBuildResult) -> list[str]:
    """Each model review yields one event whose detail is the review item's own reason."""
    reviews = [e for e in result.events if e.code == "model_review"]
    reviewed = {
        i.source_anchor: i.review.reasons
        for i in result.document.items
        if i.review.state is NativeItemReviewState.REVIEW_REQUIRED
    }
    assert len(reviews) == len(reviewed)
    for event in reviews:
        assert event.detail.startswith("AI-tolkningen markerade frågan för granskning: ")
        assert reviewed[event.anchors[0]] == (event.detail,)
    return [e.detail for e in reviews]


def _assert_no_italic_tags(document: NativeExamDocument) -> None:
    """The <i> source marks the model reads never reach student text or answer values."""
    values = [v for item in document.items for gap in item.gaps for v in gap.accepted_values]
    texts = _student_texts(document) + values
    assert not [text for text in texts if "<i>" in text or "</i>" in text]


async def test_recorded_english_matching_reviews_stay_one_item_each_without_facit():
    exam = _ENGLISH
    responses = (
        "bf26_english_1_docx_build_response_round1.json",
        "bf26_english_1_docx_build_response_round2.json",
    )
    result, chunks = await _replay(exam, *responses)
    items = result.document.items
    gold = _gold(exam)
    positions = {chunk.anchor: index for index, chunk in enumerate(chunks)}
    item_positions = [positions[i.source_anchor or ""] for i in items]

    assert len(items) == len(gold) == 53
    assert item_positions == sorted(item_positions)
    reviewed = [
        n
        for n, i in enumerate(items)
        if i.review.state is not NativeItemReviewState.REVIEW_COMPLETE
    ]
    assert reviewed == [n for n, g in enumerate(gold) if g.kind == "matching"] == [24, 25, 26]
    for n in reviewed:
        assert items[n].review.reasons == (
            "AI-tolkningen markerade frågan för granskning: Matchningsuppgift med tre "
            "definitioner och gemensamma alternativ kan inte återges som en stödd frågetyp.",
        )
        body = [
            s.text for p in items[n].body for s in p.segments if isinstance(s, NativeTextSegment)
        ]
        assert any("Write the letter of the matching option." in text for text in body)
    assert len(_assert_review_events_carry_reasons(result)) == 3
    _assert_no_facit(result, chunks, exam, *responses)


_COURSE_EXAM = "svenska_2_kursavslutande_prov_med_facit"


def _assert_course_exam_order(result: DocxBuildResult, chunks: list[DocxChunk]) -> None:
    items = result.document.items
    gold = _gold(_COURSE_EXAM)
    positions = {chunk.anchor: index for index, chunk in enumerate(chunks)}
    item_positions = [positions[i.source_anchor or ""] for i in items]
    assert len(items) == len(gold) == 24
    assert item_positions == sorted(item_positions)
    titled = [(n, i.title) for n, i in enumerate(items) if i.title]
    assert titled
    for n, title in titled:
        assert title.startswith(f"{gold[n].source_label}.")


async def test_recorded_course_exam_review_outcomes_stay_one_item_per_question():
    result, chunks = await _replay(
        _COURSE_EXAM, "svenska_2_kursavslutande_prov_docx_build_response_v2.json"
    )
    _assert_course_exam_order(result, chunks)
    reviewed = [
        (n, i.title)
        for n, i in enumerate(result.document.items)
        if i.review.state is NativeItemReviewState.REVIEW_REQUIRED
    ]
    assert [n for n, _ in reviewed] == [15, 16, 17, 18, 19]
    assert [t.split(".")[0] for _, t in reviewed if t] == [f"Fråga {k}" for k in range(16, 21)]
    prefix = "AI-tolkningen markerade frågan för granskning: "
    assert _assert_review_events_carry_reasons(result) == [
        *[f"{prefix}Uppgiftens svarssätt framgår inte av källtexten."] * 4,
        f"{prefix}Uppgiften saknar instruktion om hur påståendena ska besvaras.",
    ]


@pytest.mark.parametrize(
    "response",
    [
        "svenska_2_kursavslutande_prov_docx_build_response_v3.json",
        "svenska_2_kursavslutande_prov_docx_build_response.json",
    ],
)
async def test_recorded_course_exam_contract_keeps_one_item_per_question(response: str):
    result, chunks = await _replay(_COURSE_EXAM, response)
    _assert_course_exam_order(result, chunks)


def test_course_exam_round_request_shows_teacher_italics_to_the_model():
    chunks = exam_workspace_docx_chunker.PythonDocxExamChunker().chunk(
        content=(_FIXTURES / f"docx_corpus/{_COURSE_EXAM}.docx").read_bytes()
    )
    profile = StructuredLLMProviderProfile(
        "primary", "model", StructuredLLMEndpointKind.RESPONSES, True, 128000, 4096
    )
    request = build_round_request(
        job_id=uuid4(),
        round_number=1,
        pending=chunks,
        answer_key=(),
        failures=(),
        profile=profile,
    )
    sent = {c["anchor"]: c["text"] for c in json.loads(request.user_payload)["chunks"]}
    assert set(sent) == {c.anchor for c in chunks}
    assert "satsadverbialet <i>före</i> det finita verbet" in sent["body:0086"]
    assert request.prompt_template_version == "docx_exam_build_v5"


async def test_recorded_course_exam_keeps_inline_facit_out_of_student_text():
    response = "svenska_2_kursavslutande_prov_docx_build_response.json"
    result, chunks = await _replay(_COURSE_EXAM, response)
    _assert_no_facit(result, chunks, _COURSE_EXAM, response)
    _assert_no_italic_tags(result.document)
    for n in range(15, 20):
        item, gold = result.document.items[n], _gold(_COURSE_EXAM)[n]
        body = " ".join(
            " ".join(segment.text.split())
            for paragraph in item.body
            for segment in paragraph.segments
            if isinstance(segment, NativeTextSegment)
        )
        assert item.kind.value == gold.kind == "gap_fill"
        assert [list(g.accepted_values) for g in item.gaps] == [
            list(g.accepted_values) for g in gold.gaps
        ]
        for line in gold.prompt.split("\n")[1:]:
            for fragment in line.split("[___]"):
                assert " ".join(fragment.split()) in body


async def test_v3_recording_without_italic_marks_leaked_the_fraga_20_answer():
    response = "svenska_2_kursavslutande_prov_docx_build_response_v3.json"
    result, _ = await _replay(_COURSE_EXAM, response)
    assert any("satsadverbialet före det finita" in t for t in _student_texts(result.document))


async def test_recorded_english_current_input_keys_matching_letters_from_facit():
    response = "bf26_english_1_docx_build_response.json"
    result, chunks = await _replay(_ENGLISH, response)
    items = result.document.items
    assert len(items) == len(_gold(_ENGLISH)) == 53
    assert all(i.review.state is NativeItemReviewState.REVIEW_COMPLETE for i in items)
    assert [[list(g.accepted_values) for g in items[n].gaps] for n in (24, 25, 26)] == [
        [["B"], ["A"], ["C"]],
        [["C"], ["B"], ["A"]],
        [["B"], ["C"], ["A"]],
    ]
    _assert_no_facit(result, chunks, _ENGLISH, response)
    _assert_no_italic_tags(result.document)


async def test_empty_model_text_segments_change_no_item_in_the_recorded_course_exam():
    """The first live eval run crashed on a review item carrying a text segment with text ""."""
    name = "svenska_2_kursavslutande_prov_docx_build_response_v2.json"
    content = json.loads((_FIXTURES / name).read_text())
    empty: dict[str, object] = {"kind": "text", "text": "", "accepted_values": [], "hint": None}
    items = content["items"]
    assert [items[n]["outcome"] for n in (0, 15)] == ["converted", "review"]
    items[0]["body"][0]["segments"].append(empty)
    items[0]["body"].append({"segments": [empty]})
    items[15]["body"][0]["segments"].insert(0, empty)
    items[15]["body"].append({"segments": [empty]})
    chunks = exam_workspace_docx_chunker.PythonDocxExamChunker().chunk(
        content=(_FIXTURES / f"docx_corpus/{_COURSE_EXAM}.docx").read_bytes()
    )
    converter, provider = ports()
    provider.complete_structured.return_value = StructuredLLMResponse(
        content, "completed", StructuredLLMUsage()
    )
    result = await converter.convert(
        job_id=uuid4(),
        document_id=uuid4(),
        filename=f"{_COURSE_EXAM}.docx",
        source_sha256="a" * 64,
        chunks=chunks,
    )
    recorded, _ = await _replay(_COURSE_EXAM, name)
    assert provider.complete_structured.await_count == 1
    assert result.document.items == recorded.document.items
    assert [e.code for e in result.events] == [e.code for e in recorded.events]
