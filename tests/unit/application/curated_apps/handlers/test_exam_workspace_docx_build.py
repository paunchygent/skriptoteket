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
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_admission import (
    admit_batch,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_rounds import (
    build_round_request,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_state import (
    DocxBuildState,
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
    NativeExamItemKind,
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


async def test_recorded_quiz_builds_all_items_and_exports_qti():
    exam = "chapter_4_poetry_and_lyrics_quiz_med_facit"
    result, chunks = await _replay(exam, *_v7_rounds(exam))
    items = result.document.items
    assert result.document.title == (
        "Chapter 4: Poetry and Lyrics — Vocabulary and Terminology Quiz — answer key"
    )
    assert len(items) == len(_gold(exam)) == 28
    assert sum(item.points or 0 for item in items) == 28
    assert [item.kind.value for item in items] == [g.kind for g in _gold(exam)]
    assert all(i.review.state is NativeItemReviewState.REVIEW_COMPLETE for i in items)
    assert native_export_blockers(result.document) == ()
    package, report = build_native_examnet_qti_package(
        result.document, package_name="probe", qti_writer=ExamNetQtiPackageWriter()
    )
    assert json.loads(report)["package_status"] == "passed"
    with zipfile.ZipFile(io.BytesIO(package)) as archive:
        assert "imsmanifest.xml" in archive.namelist()
    _assert_no_facit(result, chunks, exam, *_v7_rounds(exam))


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


def _v7_rounds(exam: str) -> tuple[str, ...]:
    """The prompt v7 live recording rounds of one corpus exam, in order."""
    return tuple(
        str(path.relative_to(_FIXTURES))
        for path in sorted((_FIXTURES / "docx_build_v7" / exam).glob("round*.json"))
    )


def _gold(exam: str) -> tuple[GoldItem, ...]:
    path = _FIXTURES / f"docx_corpus/gold/{exam}.json"
    questions: tuple[GoldItem, ...] = GoldExam.model_validate_json(path.read_bytes()).questions
    return questions


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


async def test_recorded_english_matching_items_keep_their_lists_and_gold_pairs():
    exam = _ENGLISH
    result, chunks = await _replay(exam, *_v7_rounds(exam))
    items = result.document.items
    gold = _gold(exam)
    assert len(items) == len(gold) == 53
    matching = [n for n, i in enumerate(items) if i.kind is NativeExamItemKind.MATCHING]
    assert matching == [n for n, g in enumerate(gold) if g.kind == "matching"]
    assert matching
    for n in matching:
        item = items[n]
        assert item.review.state is NativeItemReviewState.REVIEW_COMPLETE
        left = {entry.left_id: entry.text for entry in item.match_left}
        right = {entry.right_id: entry.text for entry in item.match_right}
        pairs = {(left[p.left_id], right[p.right_id]) for p in item.answer_key.match_pairs}
        assert pairs == {(pair.left, pair.right) for pair in gold[n].pairs}
    assert native_export_blockers(result.document) == ()
    _assert_no_facit(result, chunks, exam, *_v7_rounds(exam))
    _assert_no_italic_tags(result.document)


async def test_recorded_english_vocabulary_section_is_one_parent_of_its_gap_fill_items():
    result, chunks = await _replay(_ENGLISH, *_v7_rounds(_ENGLISH))
    document = result.document
    wording = next(c.text for c in chunks if c.anchor == "body:0006")

    parent = document.parents[0]
    assert parent.parent_id == "parent_001"
    assert parent.instruction == (wording,)
    children = [document.item_by_id(item_id) for item_id in parent.item_ids]
    assert children == list(document.items[:24])
    assert {c.kind for c in children} == {NativeExamItemKind.GAP_FILL}
    assert wording not in document.instructions
    assert not any(wording in " ".join(c.plain_text_lines()) for c in children)
    assert native_export_blockers(document) == ()


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
        assert not title.startswith(gold[n].source_label)


def _admitted(exam: str, recording: str) -> DocxBuildState:
    chunks = exam_workspace_docx_chunker.PythonDocxExamChunker().chunk(
        content=(_FIXTURES / f"docx_corpus/{exam}.docx").read_bytes()
    )
    state = DocxBuildState(uuid4(), uuid4(), f"{exam}.docx", "a" * 64, chunks)
    admit_batch(json.loads((_FIXTURES / recording).read_text()), state)
    return state


_COURSE_V2 = "svenska_2_kursavslutande_prov_docx_build_response_v2.json"


def test_recorded_course_exam_review_outcomes_stay_one_item_per_question():
    state = _admitted(_COURSE_EXAM, _COURSE_V2)
    reviewed = [
        (anchors, item)
        for item, anchors in state.accepted
        if item.review.state is NativeItemReviewState.REVIEW_REQUIRED
    ]
    assert [anchors[0] for anchors, _ in reviewed] == [
        "body:0061",
        "body:0067",
        "body:0073",
        "body:0079",
        "body:0085",
    ]
    assert [item.title.split(".")[0] for _, item in reviewed if item.title] == [
        f"Fråga {k}" for k in range(16, 21)
    ]
    prefix = "AI-tolkningen markerade frågan för granskning: "
    assert [e.detail for e in state.events if e.code == "model_review"] == [
        *[f"{prefix}Uppgiftens svarssätt framgår inte av källtexten."] * 4,
        f"{prefix}Uppgiften saknar instruktion om hur påståendena ska besvaras.",
    ]
    assert all(item.review.reasons for _, item in reviewed)


def test_recorded_course_exam_items_keeping_their_printed_number_are_rejected_and_stay_pending():
    state = _admitted(_COURSE_EXAM, _COURSE_V2)
    kept = ("body:0093", "body:0099", "body:0105", "body:0111")
    accepted = {anchors[0] for _, anchors in state.accepted}
    pending = {chunk.anchor for chunk in state.pending}

    assert accepted.isdisjoint(kept)
    assert set(kept) <= pending
    rejected = [e for e in state.events if e.code == "source_rule" and e.anchors[0] in kept]
    assert [e.anchors[0] for e in rejected] == list(kept)
    for event in rejected:
        assert f"question number that {event.anchors[0]} prints" in event.detail
        assert event.anchors[0] in state.reasons


@pytest.mark.parametrize("version", ["docx_build_v6", "docx_build_v7"])
async def test_recorded_course_exam_contract_keeps_one_item_per_question(version: str):
    result, chunks = await _replay(_COURSE_EXAM, f"{version}/{_COURSE_EXAM}/round1.json")
    _assert_course_exam_order(result, chunks)


async def test_course_exam_round_request_shows_teacher_italics_to_the_model():
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
    assert request.prompt_template_version == "docx_exam_build_v9"


async def test_recorded_course_exam_keeps_inline_facit_out_of_student_text():
    responses = _v7_rounds(_COURSE_EXAM)
    result, chunks = await _replay(_COURSE_EXAM, *responses)
    _assert_no_facit(result, chunks, _COURSE_EXAM, *responses)
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


def test_empty_model_text_segments_change_no_item_in_the_recorded_course_exam():
    """The first live eval run crashed on a review item carrying a text segment with text ""."""
    content = json.loads((_FIXTURES / _COURSE_V2).read_text())
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
    mutated = DocxBuildState(uuid4(), uuid4(), f"{_COURSE_EXAM}.docx", "a" * 64, chunks)
    admit_batch(content, mutated)
    recorded = _admitted(_COURSE_EXAM, _COURSE_V2)
    assert [item for item, _ in mutated.accepted] == [item for item, _ in recorded.accepted]
    assert [e.code for e in mutated.events] == [e.code for e in recorded.events]
