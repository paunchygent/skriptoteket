"""A fault in one question only ever affects that question (TASK-SKRIPT-39-05-04 D25, D32).

Each test replays the recorded live run of one exam at its recorded batch size (16 families
per batch) and corrupts one recorded batch reply, or makes one post-batch step fail on one
batch's content. Only the affected questions become review items holding their own source
text at their place; every other item equals the uncorrupted run, and the conversion
finishes. A lost job lease still stops the conversion.
"""

from collections.abc import Callable, Mapping
from types import MappingProxyType
from uuid import UUID

import pytest
from pydantic import JsonValue

from skriptoteket.application.curated_apps.handlers import exam_workspace_docx_pipeline
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_state import (
    DocxBuildState,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_run import (
    DocxConversionOutcome,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMProviderProfile,
    StructuredLLMRequest,
    StructuredLLMResponse,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import DocxBuildResult
from skriptoteket.domain.curated_apps.exam_workspace.docx_batches import QuestionFamily
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
    NativeExamItem,
    NativeExamItemKind,
    NativeItemReviewState,
    NativeParseOrigin,
    NativeTextSegment,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.protocols.docx_conversion_progress import ConversionUpdate
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import (
    RecordingProgress,
    ReplayProvider,
    build_replay,
    corpus_chunks,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

_EXAM = "bf26_english_1_unit_test_kap_1_2_med_facit"
Corruption = Callable[[dict[str, JsonValue]], None]


class _CorruptedProvider(ReplayProvider):
    """Serve the recordings, with one batch reply changed by ``corrupt``."""

    def __init__(self, request_id: str, corrupt: Corruption) -> None:
        super().__init__(_EXAM)
        self._request_id = request_id
        self._corrupt = corrupt

    async def complete_structured(
        self, *, request: StructuredLLMRequest, profile: StructuredLLMProviderProfile
    ) -> StructuredLLMResponse:
        response = await super().complete_structured(request=request, profile=profile)
        if request.item_id != self._request_id:
            return response
        content = dict(response.content)
        self._corrupt(content)
        return StructuredLLMResponse(content, response.finish_reason, response.usage)


def _first_anchor(entry: JsonValue) -> JsonValue:
    assert isinstance(entry, dict)
    anchors = entry["source_anchors"]
    assert isinstance(anchors, list)
    return anchors[0]


def _item_at(content: dict[str, JsonValue], anchor: str) -> dict[str, JsonValue]:
    items = content["items"]
    assert isinstance(items, list)
    found = next(i for i in items if _first_anchor(i) == anchor)
    assert isinstance(found, dict)
    return found


async def _convert(provider: ReplayProvider | None = None) -> DocxConversionOutcome:
    replay = build_replay(_EXAM, provider=provider)
    return await replay.pipeline.convert(job=replay.job())


def _by_anchor(outcome: DocxConversionOutcome) -> dict[str | None, NativeExamItem]:
    return {item.source_anchor: item for item in outcome.result.document.items}


def _comparable(item: NativeExamItem) -> NativeExamItem:
    """The item with its document-position id and sequence set to those of a first item."""
    return item.model_copy(update={"item_id": "item_001", "sequence": 1})


def _text(item: NativeExamItem) -> list[str]:
    return [
        segment.text
        for paragraph in item.body
        for segment in paragraph.segments
        if isinstance(segment, NativeTextSegment)
    ]


def _question_of(update: ConversionUpdate, item_id: str) -> str:
    return next(qid for qid, ids in update.item_ids.items() if item_id in ids)


def _assert_only_questions_reviewed(
    baseline: DocxConversionOutcome, outcome: DocxConversionOutcome, anchors: set[str]
) -> None:
    """The questions starting at ``anchors`` are placed source review items; nothing else
    differs from the uncorrupted run."""
    chunks = corpus_chunks(_EXAM)
    position = {chunk.anchor: n for n, chunk in enumerate(chunks)}
    text = {chunk.anchor: chunk.text for chunk in chunks}
    assert outcome.update.pending == ()
    before, after = _by_anchor(baseline), _by_anchor(outcome)
    assert set(before) == set(after), "a question gained or lost an item"
    ordered = [item.source_anchor or "" for item in outcome.result.document.items]
    assert [position[a] for a in ordered] == sorted(position[a] for a in ordered)
    for anchor, item in after.items():
        if anchor not in anchors:
            assert _comparable(item) == _comparable(before[anchor]), f"{anchor} changed"
            continue
        assert item.kind is NativeExamItemKind.FREE_TEXT
        assert item.review.state is NativeItemReviewState.REVIEW_REQUIRED
        assert item.review.parse_origin is NativeParseOrigin.DETERMINISTIC
        assert item.review.reasons, f"{anchor} names no failure reason"
        qid = _question_of(outcome.update, item.item_id)
        assert outcome.update.item_ids[qid] == (item.item_id,), f"{qid} is not one item"
        lines = _text(item)
        assert text[anchor] in lines, f"{anchor} lost its source text"
        source = "\n".join(text.values())
        assert all(line in source for line in lines), f"{anchor} shows text the source lacks"


@pytest.fixture
async def baseline() -> DocxConversionOutcome:
    return await _convert()


async def test_a_review_reply_with_an_empty_body_reviews_only_its_question(baseline):
    def corrupt(content: dict[str, JsonValue]) -> None:
        entry = _item_at(content, "body:0015")
        entry.update(outcome="review", review_reason="oklar", body=[])

    outcome = await _convert(_CorruptedProvider("docx_w1-01", corrupt))

    _assert_only_questions_reviewed(baseline, outcome, {"body:0015"})
    codes = [e.code for e in outcome.result.events if "body:0015" in e.anchors]
    assert "item_unparsed" in codes


async def test_a_choice_reply_pairing_undeclared_texts_reviews_only_its_question(baseline):
    def corrupt(content: dict[str, JsonValue]) -> None:
        entry = _item_at(content, "body:0081")
        entry["match_pairs"] = [{"left": "not listed", "right": "not listed either"}]

    outcome = await _convert(_CorruptedProvider("docx_w1-04", corrupt))

    _assert_only_questions_reviewed(baseline, outcome, {"body:0081"})


async def test_a_title_of_answer_key_wording_alone_leaves_every_question_converted(baseline):
    def corrupt(content: dict[str, JsonValue]) -> None:
        content["title"] = {"text": "(Answer key)", "source_anchors": ["body:0002"], "points": None}

    outcome = await _convert(_CorruptedProvider("docx_w1-01", corrupt))

    assert "title_unparsed" in [e.code for e in outcome.result.events]
    after = _by_anchor(outcome)
    for anchor, item in _by_anchor(baseline).items():
        assert _comparable(after[anchor]) == _comparable(item), f"{anchor} changed"
    assert "body:0002" in after, "the unusable title's chunk is not kept for review"


def _converted_at(state: DocxBuildState, anchor: str) -> bool:
    return any(
        item.source_anchor == anchor and item.review.parse_origin is NativeParseOrigin.LLM_PARSED
        for item, _ in state.accepted
    )


_W1_02 = {"body:0039", "body:0041", "body:0043", "body:0045", "body:0047", "body:0049"}
_W1_02 |= {"body:0051", "body:0053", "body:0097", "body:0099", "body:0101", "body:0103"}
_W1_02 |= {"body:0105", "body:0107", "body:0109", "body:0111"}


async def test_a_merge_failing_on_one_batch_reviews_only_that_batch(baseline, monkeypatch):
    merge = exam_workspace_docx_pipeline.merge_batch

    def failing_merge(target: DocxBuildState, batch: DocxBuildState, title: frozenset[str]) -> None:
        if _converted_at(batch, "body:0039"):
            raise ValueError("merge met content it cannot hold")
        merge(target, batch, title)

    monkeypatch.setattr(exam_workspace_docx_pipeline, "merge_batch", failing_merge)
    outcome = await _convert()

    _assert_only_questions_reviewed(baseline, outcome, _W1_02)
    assert "batch_merge_failed" in [e.code for e in outcome.result.events]


async def test_a_provisional_build_failing_on_one_batch_reviews_only_that_batch(
    baseline, monkeypatch
):
    build = exam_workspace_docx_pipeline.provisional_result

    def failing_build(
        state: DocxBuildState,
        families: tuple[QuestionFamily, ...],
        pending: frozenset[str],
        governed: Mapping[str, frozenset[str]],
    ) -> DocxBuildResult:
        if _converted_at(state, "body:0039"):
            raise KeyError("provisional build met content it cannot hold")
        return build(state, families, pending, governed)

    monkeypatch.setattr(exam_workspace_docx_pipeline, "provisional_result", failing_build)
    outcome = await _convert()

    _assert_only_questions_reviewed(baseline, outcome, _W1_02)


async def test_a_progress_update_failing_on_one_batch_reviews_only_that_batch(
    baseline, monkeypatch
):
    update = exam_workspace_docx_pipeline.conversion_update

    def failing_update(
        document: NativeExamDocument,
        families: tuple[QuestionFamily, ...],
        filled: tuple[str, ...],
        pending: tuple[str, ...],
        *,
        assets_by_id: Mapping[str, bytes] = MappingProxyType({}),
    ) -> ConversionUpdate:
        converted = any(
            i.source_anchor == "body:0039" and i.review.parse_origin is NativeParseOrigin.LLM_PARSED
            for i in document.items
        )
        if converted and pending:
            raise TypeError("progress update met content it cannot hold")
        return update(document, families, filled, pending, assets_by_id=assets_by_id)

    monkeypatch.setattr(exam_workspace_docx_pipeline, "conversion_update", failing_update)
    outcome = await _convert()

    _assert_only_questions_reviewed(baseline, outcome, _W1_02)


async def test_an_item_a_later_update_breaks_never_reaches_final_assembly(baseline, monkeypatch):
    mark = exam_workspace_docx_pipeline.with_type_check_mark

    def breaking_mark(state: DocxBuildState) -> None:
        mark(state)
        state.accepted = [
            (
                item.model_copy(update={"points": -1})
                if item.source_anchor == "body:0019"
                else item,
                a,
            )
            for item, a in state.accepted
        ]

    monkeypatch.setattr(exam_workspace_docx_pipeline, "with_type_check_mark", breaking_mark)
    outcome = await _convert()

    _assert_only_questions_reviewed(baseline, outcome, {"body:0019"})


async def test_a_lost_job_lease_still_stops_the_conversion():
    class LostLease(RecordingProgress):
        async def batch_ready(
            self, *, worker_id: str, job_id: UUID, update: ConversionUpdate
        ) -> None:
            raise DomainError(code=ErrorCode.CONFLICT, message="lease is no longer owned")

    replay = build_replay(_EXAM, progress=LostLease())
    with pytest.raises(DomainError) as raised:
        await replay.pipeline.convert(job=replay.job())
    assert raised.value.code is ErrorCode.CONFLICT
