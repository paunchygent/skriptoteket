"""A fault in one question or one batch never spreads beyond it (TASK-SKRIPT-39-05-04 D25, D32).

Each test replays the recorded live run of the BF26 English exam at its recorded batch size
(16 families per batch), then corrupts one recorded reply entry or makes one post-batch step
fail on the current batch's content. Only the affected questions become review items holding
their own source text at their place; every other item equals the uncorrupted run, and the
conversion finishes. A lost job lease still stops the conversion.
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
from skriptoteket.domain.curated_apps.exam_workspace.docx_batches import (
    QuestionFamily,
    question_families,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_manifest import manifest_from_output
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
    recording,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

_EXAM = "bf26_english_1_unit_test_kap_1_2_med_facit"
# Current recordings: w1-01 carries the converted item at body:0015, w1-02 the one at
# body:0041, and w1-04 the one at body:0075.
_EMPTY_BODY_BATCH = "docx_w1-01"
_EMPTY_BODY_ANCHOR = "body:0015"
_PAIRED_TEXTS_BATCH = "docx_w1-04"
_PAIRED_TEXTS_ANCHOR = "body:0075"
_BATCH_ANCHOR = "body:0041"
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


def _anchor(item: NativeExamItem) -> str:
    assert item.source_anchor is not None
    return item.source_anchor


def _converted_at(state: DocxBuildState, anchor: str) -> bool:
    return any(
        item.source_anchor == anchor and item.review.parse_origin is NativeParseOrigin.LLM_PARSED
        for item, _ in state.accepted
    )


def _assert_only_reviewed(
    baseline: DocxConversionOutcome, outcome: DocxConversionOutcome, expected_changed: set[str]
) -> None:
    """The anchors in ``expected_changed`` and only they become deterministic review items
    holding their source text; every other item equals the uncorrupted run."""
    chunks = corpus_chunks(_EXAM)
    text = {chunk.anchor: chunk.text for chunk in chunks}
    assert outcome.update.pending == ()
    before, after = _by_anchor(baseline), _by_anchor(outcome)
    assert set(before) == set(after), "a question gained or lost an item"
    changed = {
        anchor for anchor in before if _comparable(before[anchor]) != _comparable(after[anchor])
    }
    assert changed == expected_changed, "a fault spread beyond the affected questions"
    for anchor in changed:
        item = after[anchor]
        assert item.kind is NativeExamItemKind.FREE_TEXT
        assert item.review.state is NativeItemReviewState.REVIEW_REQUIRED
        assert item.review.parse_origin is NativeParseOrigin.DETERMINISTIC
        assert item.review.reasons, f"{anchor} names no failure reason"
        source_anchor = _anchor(item)
        lines = _text(item)
        assert text[source_anchor] in lines, f"{source_anchor} lost its source text"
        source = "\n".join(text.values())
        assert all(line in source for line in lines), f"{source_anchor} shows text the source lacks"


def _assert_question_reviewed(outcome: DocxConversionOutcome, question_id: str) -> None:
    """``question_id`` is one deterministic review item holding its own source text."""
    items = {item.item_id: item for item in outcome.result.document.items}
    ids = outcome.update.item_ids[question_id]
    assert len(ids) == 1, f"{question_id} is not one review item"
    item = items[ids[0]]
    assert item.kind is NativeExamItemKind.FREE_TEXT
    assert item.review.state is NativeItemReviewState.REVIEW_REQUIRED
    assert item.review.parse_origin is NativeParseOrigin.DETERMINISTIC
    assert item.review.reasons, f"{question_id} names no failure reason"
    text = {chunk.anchor: chunk.text for chunk in corpus_chunks(_EXAM)}
    assert text[item.source_anchor or ""] in _text(item), f"{question_id} lost its source text"


def _batch_questions(failed_claims: frozenset[str]) -> set[str]:
    """The current families whose claims the failed batch held."""
    chunks = corpus_chunks(_EXAM)
    manifest = manifest_from_output(recording(_EXAM, "docx_grouping_1"), chunks)
    return {
        family.question_id
        for family in question_families(manifest, chunks)
        if family.claims & failed_claims
    }


def _assert_batch_reviewed(
    baseline: DocxConversionOutcome, outcome: DocxConversionOutcome, reviewed: set[str]
) -> None:
    """Every question of the failed batch is one review item; every other question stays."""
    assert reviewed, "no batch was affected"
    assert len(reviewed) >= 2, "one batch covers several questions"
    items = {item.item_id: item for item in outcome.result.document.items}
    expected_changed = {
        _anchor(items[item_id])
        for question_id in reviewed
        for item_id in outcome.update.item_ids[question_id]
    }
    _assert_only_reviewed(baseline, outcome, expected_changed)
    for question_id in reviewed:
        _assert_question_reviewed(outcome, question_id)


@pytest.fixture
async def baseline() -> DocxConversionOutcome:
    return await _convert()


async def test_a_review_reply_with_an_empty_body_reviews_only_its_question(baseline):
    def corrupt(content: dict[str, JsonValue]) -> None:
        entry = _item_at(content, _EMPTY_BODY_ANCHOR)
        entry.update(outcome="review", review_reason="oklar", body=[])

    outcome = await _convert(_CorruptedProvider(_EMPTY_BODY_BATCH, corrupt))

    _assert_only_reviewed(baseline, outcome, {_EMPTY_BODY_ANCHOR})
    codes = [e.code for e in outcome.result.events if _EMPTY_BODY_ANCHOR in e.anchors]
    assert "item_unparsed" in codes


async def test_a_reply_pairing_undeclared_texts_reviews_only_its_question(baseline):
    def corrupt(content: dict[str, JsonValue]) -> None:
        entry = _item_at(content, _PAIRED_TEXTS_ANCHOR)
        entry["match_pairs"] = [{"left": "not listed", "right": "not listed either"}]

    outcome = await _convert(_CorruptedProvider(_PAIRED_TEXTS_BATCH, corrupt))

    _assert_only_reviewed(baseline, outcome, {_PAIRED_TEXTS_ANCHOR})
    codes = [e.code for e in outcome.result.events if _PAIRED_TEXTS_ANCHOR in e.anchors]
    assert "item_unparsed" in codes


async def test_a_title_of_answer_key_wording_alone_leaves_every_question_converted(baseline):
    def corrupt(content: dict[str, JsonValue]) -> None:
        content["title"] = {"text": "(Answer key)", "source_anchors": ["body:0002"], "points": None}

    outcome = await _convert(_CorruptedProvider("docx_w1-01", corrupt))

    assert "title_unparsed" in [e.code for e in outcome.result.events]
    after = _by_anchor(outcome)
    for anchor, item in _by_anchor(baseline).items():
        assert _comparable(after[anchor]) == _comparable(item), f"{anchor} changed"
    assert "body:0002" in after, "the unusable title's chunk is not kept for review"


async def test_a_merge_failing_on_one_batch_reviews_only_that_batch(baseline, monkeypatch):
    merge = exam_workspace_docx_pipeline.merge_batch
    failed: list[frozenset[str]] = []

    def failing_merge(target: DocxBuildState, batch: DocxBuildState, title: frozenset[str]) -> None:
        if _converted_at(batch, _BATCH_ANCHOR) and batch.claimable is not None:
            failed.append(batch.claimable)
            raise ValueError("merge met content it cannot hold")
        merge(target, batch, title)

    monkeypatch.setattr(exam_workspace_docx_pipeline, "merge_batch", failing_merge)
    outcome = await _convert()

    assert failed, "the merge never met the current batch's content"
    _assert_batch_reviewed(baseline, outcome, _batch_questions(failed[0]))
    assert "batch_merge_failed" in [e.code for e in outcome.result.events]


async def test_a_provisional_build_failing_on_one_batch_reviews_only_that_batch(
    baseline, monkeypatch
):
    build = exam_workspace_docx_pipeline.provisional_result
    previous_pending: list[frozenset[str] | None] = [None]
    failed: list[set[str]] = []

    def failing_build(
        state: DocxBuildState,
        families: tuple[QuestionFamily, ...],
        pending: frozenset[str],
        governed: Mapping[str, frozenset[str]],
    ) -> DocxBuildResult:
        if _converted_at(state, _BATCH_ANCHOR):
            everything = frozenset(f.question_id for f in families)
            before = previous_pending[0] if previous_pending[0] is not None else everything
            failed.append(set(before) - set(pending))
            raise KeyError("provisional build met content it cannot hold")
        previous_pending[0] = pending
        return build(state, families, pending, governed)

    monkeypatch.setattr(exam_workspace_docx_pipeline, "provisional_result", failing_build)
    outcome = await _convert()

    assert failed, "the provisional build never met the current batch's content"
    _assert_batch_reviewed(baseline, outcome, failed[0])


async def test_a_progress_update_failing_on_one_batch_reviews_only_that_batch(
    baseline, monkeypatch
):
    update = exam_workspace_docx_pipeline.conversion_update
    previous_filled: list[set[str]] = [set()]
    failed: list[set[str]] = []

    def failing_update(
        document: NativeExamDocument,
        families: tuple[QuestionFamily, ...],
        filled: tuple[str, ...],
        pending: tuple[str, ...],
        *,
        assets_by_id: Mapping[str, bytes] = MappingProxyType({}),
    ) -> ConversionUpdate:
        converted = any(
            item.source_anchor == _BATCH_ANCHOR
            and item.review.parse_origin is NativeParseOrigin.LLM_PARSED
            for item in document.items
        )
        if converted and pending:
            failed.append(set(filled) - previous_filled[0])
            raise TypeError("progress update met content it cannot hold")
        previous_filled[0] = set(filled)
        return update(document, families, filled, pending, assets_by_id=assets_by_id)

    monkeypatch.setattr(exam_workspace_docx_pipeline, "conversion_update", failing_update)
    outcome = await _convert()

    assert failed, "the progress update never met the current batch's content"
    _assert_batch_reviewed(baseline, outcome, failed[0])


async def test_an_item_a_later_update_breaks_never_reaches_final_assembly(baseline, monkeypatch):
    mark = exam_workspace_docx_pipeline.with_type_check_mark

    def breaking_mark(state: DocxBuildState) -> None:
        mark(state)
        state.accepted = [
            (
                item.model_copy(update={"points": -1})
                if item.source_anchor == "body:0019"
                else item,
                anchors,
            )
            for item, anchors in state.accepted
        ]

    monkeypatch.setattr(exam_workspace_docx_pipeline, "with_type_check_mark", breaking_mark)
    outcome = await _convert()

    _assert_only_reviewed(baseline, outcome, {"body:0019"})


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
