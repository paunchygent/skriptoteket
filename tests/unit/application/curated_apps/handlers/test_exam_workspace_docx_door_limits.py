"""Door limits across DOCX conversion and content-tag jobs (TASK-SKRIPT-41-01-03 B3).

Proves the limit rule for multi-call jobs through a synthetic three-question
exam over a scripted provider door: a refused batch fails only its items and
stops later calls, a content refusal keeps the conversion, a grouping refusal
fails everything pending, the overage cap stops the next call, and a job
admitted before the pool ran out finishes as paid overage while the next job
is refused at grouping. The content-suggestion and DOCX job handlers map both
refusals to ``ai_limit`` plus their code, never ``unexpected_error``.
"""

from __future__ import annotations

import io
import json
from typing import Any
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest
from docx import Document
from pydantic import JsonValue

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJob,
    ExamAnswerKeyEnrichmentJobStatus,
    ExamAnswerKeySourceKind,
)
from skriptoteket.application.curated_apps.exam_content_tagging import (
    ExamContentTagSuggester,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_content_tags import (
    ProcessExamContentSuggestionsHandler,
    content_response,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_run import (
    DocxConversionJob,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_serial_uow import (
    SerializedUnitOfWork,
)
from skriptoteket.application.curated_apps.item_type_labeling import TwoPassItemTypeLabeler
from skriptoteket.config import Settings
from skriptoteket.di.docx_conversion import build_docx_conversion_pipeline
from skriptoteket.domain.curated_apps.exam_workspace.exam_content_tags import ExamContentItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import ExamCourseChoice
from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.llm_door import AiDailyLimit, AiDailyLimitReached, AiJobOverageCapReached
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_chunker import (  # noqa: E501
    PythonDocxExamChunker,
)
from skriptoteket.infrastructure.llm.openai.answer_key_structured_provider import (
    OpenAIAnswerKeyStructuredProvider,
)
from skriptoteket.protocols.item_type_labeler import (
    ItemTypeLabel,
    ItemTypeLabeling,
    ItemTypeLabelResult,
    LabelingItem,
    LabelingRequest,
    LabelingUsage,
    LabelRoute,
    MeteredItemTypeLabelerProtocol,
    SecondPassItemTypeLabelerProtocol,
    SecondPassLabel,
)
from skriptoteket.protocols.llm_door import DoorOperation, DoorReply
from tests.fixtures.application_fixtures import FakeUow
from tests.fixtures.profile_app_continuation_support import UserRepositoryStub
from tests.unit.application.curated_apps.handlers.answer_key_enrichment_test_support import (
    FixedClock,
    InMemoryEnrichmentJobRepository,
)
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import (
    NoSleep,
    NoTransaction,
)
from tests.unit.application.curated_apps.handlers.test_exam_workspace_docx_jobs import (
    claim,
    environment,
)
from tests.unit.application.curated_apps.handlers.workspace_suggestion_handler_support import (
    NOW,
    suggestion_document,
    suggestion_item,
)
from tests.unit.llm_door_fakes import (
    DoorSent,
    RecordingDoor,
    fixture_caller,
    json_reply,
    user_with_role,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

_LIMIT_MESSAGE = "Du har nått dagens gräns för AI-hjälp. Försök igen i morgon."
_CONTENT = (ExamContentItem(id="course:bullet", text="Centralt innehåll"),)


def _exam_bytes() -> bytes:
    document = Document()
    document.add_paragraph("Limit exam", style="Title")
    document.add_paragraph("1. First question.")
    document.add_paragraph("2. Second question.")
    document.add_paragraph("3. Third question.")
    document.add_paragraph("4. Fourth question.")
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def _grouping_for(anchors: list[str]) -> dict[str, Any]:
    return {
        "title_anchors": [anchors[0]],
        "questions": [
            {
                "id": f"q{index}",
                "anchors": [anchor],
                "subpart_anchors": [],
                "answer_key_anchors": [],
            }
            for index, anchor in enumerate(anchors[1:], start=1)
        ],
        "shared_contexts": [],
        "header_anchors": [],
    }


def _free_text_answer(name: str) -> dict[str, Any]:
    return {
        "type": "choice",
        "name": name,
        "choice": "free_text",
        "probabilities": [
            {"value": label.value, "probability": 1.0 if label is ItemTypeLabel.FREE_TEXT else 0.0}
            for label in ItemTypeLabel
        ],
    }


def _converted_item(anchors: list[str], index: int) -> dict[str, Any]:
    return {
        "source_anchors": anchors,
        "outcome": "converted",
        "conflict_kind": None,
        "review_reason": None,
        "kind": "free_text",
        "printed_label": str(index),
        "body": [
            {"segments": [{"kind": "text", "text": "Converted.", "accepted_values": []}]},
        ],
        "points": 1,
        "choices": [],
        "match_left": [],
        "match_right": [],
        "match_pairs": [],
        "criteria": [],
        "key_source": None,
        "facit_text": None,
    }


def _responses_envelope(content: JsonValue) -> JsonValue:
    return {
        "status": "completed",
        "output_text": json.dumps(content),
        "usage": {"input_tokens": 10, "output_tokens": 10},
    }


class _DoorScript:
    """Serve one synthetic exam at the door seam with scripted charges and refusals."""

    def __init__(
        self,
        *,
        grouping: dict[str, JsonValue],
        batch_charge_usd_micros: int = 0,
        refuse_grouping: bool = False,
        refuse_batch_calls: tuple[int, ...] = (),
        refuse_content: bool = False,
        refuse_non_overage_after_first: bool = False,
    ) -> None:
        self._grouping = grouping
        self._batch_charge = batch_charge_usd_micros
        self._refuse_grouping = refuse_grouping
        self._refuse_batch_calls = refuse_batch_calls
        self._refuse_content = refuse_content
        self._refuse_non_overage_after_first = refuse_non_overage_after_first
        self.calls = 0
        self.batch_calls = 0
        self.door = RecordingDoor(self.respond)

    def respond(self, sent: DoorSent) -> DoorReply:
        self.calls += 1
        if self._refuse_non_overage_after_first and not sent.allow_paid_overage and self.calls > 1:
            raise AiDailyLimitReached(limit=AiDailyLimit.POOL)
        if sent.operation is DoorOperation.DECISIONS:
            payload: Any = sent.payload
            questions = payload["questions"]
            if questions[0]["name"].startswith("kind_"):
                return json_reply({"answers": [_free_text_answer(q["name"]) for q in questions]})
            if self._refuse_content:
                raise AiDailyLimitReached(limit=AiDailyLimit.USER_SHARE)
            return json_reply(
                {
                    "answers": [
                        {
                            "type": "choice",
                            "name": q["name"],
                            "choice": "c0",
                            "probabilities": [
                                {"value": "c0", "probability": 0.9},
                                {"value": "none", "probability": 0.1},
                            ],
                        }
                        for q in questions
                    ],
                    "usage": {"input_tokens": 9},
                }
            )
        payload = sent.payload
        assert isinstance(payload["input"], list)
        content = payload["input"][0]["content"]
        assert isinstance(content, list)
        text = next(part["text"] for part in content if part["type"] == "input_text")
        try:
            inner = json.loads(text)
        except ValueError:
            inner = None
        if isinstance(inner, dict) and "item_kinds" in inner:
            self.batch_calls += 1
            if self.batch_calls in self._refuse_batch_calls:
                raise AiDailyLimitReached(limit=AiDailyLimit.POOL)
            items: list[Any] = [
                _converted_item(question, index)
                for index, question in enumerate(inner["questions"], start=1)
            ]
            return json_reply(
                _responses_envelope(
                    {
                        "title": None,
                        "instructions": [],
                        "answer_key_anchors": [],
                        "items": items,
                    }
                ),
                overage_usd_micros=self._batch_charge or None,
            )
        if self._refuse_grouping:
            raise AiDailyLimitReached(limit=AiDailyLimit.POOL)
        return json_reply(_responses_envelope(self._grouping))


def _convert(script: _DoorScript, *, course_key: str | None = None):
    from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import (
        RecordingProgress as _Progress,
    )

    content = _exam_bytes()
    chunks = PythonDocxExamChunker().chunk(content=content)
    progress = _Progress()
    pipeline = build_docx_conversion_pipeline(
        door=script.door,
        provider=OpenAIAnswerKeyStructuredProvider(door=script.door, timeout_seconds=5.0),
        sleeper=NoSleep(),
        uow=SerializedUnitOfWork(NoTransaction()),
        settings=Settings.model_construct(
            LLM_ANSWER_KEY_ENABLED=True,
            LLM_DOCX_BATCH_FAMILIES=1,
            LLM_ITEM_LABELER_TIMEOUT_SECONDS=5,
            LLM_DOCX_CONVERSION_TIMEOUT_SECONDS=5,
        ),
        progress=progress,
    )
    job = DocxConversionJob(
        origin_kind="docx_import",
        job_id=uuid4(),
        worker_id="limit-worker",
        document_id=uuid4(),
        filename="limit.docx",
        source_sha256="0" * 64,
        source_docx=content,
        chunks=chunks,
        course_key=course_key,
        caller=fixture_caller(),
    )
    return pipeline, job


async def _convert_with(script: _DoorScript, monkeypatch, *, course_key=None):
    monkeypatch.setattr(
        "skriptoteket.application.curated_apps.handlers.exam_workspace_docx_pipeline."
        "load_exam_content_catalog",
        lambda: {"SVESVE02": _CONTENT},
    )
    pipeline, job = _convert(script, course_key=course_key)
    outcome = await pipeline.convert(job=job)
    return outcome, job


def _sent_batches(script: _DoorScript) -> list[dict[str, Any]]:
    """The batch request bodies sent, in order; grouping prose is not JSON."""
    found: list[dict[str, Any]] = []
    for sent in script.door.sent:
        if sent.operation is not DoorOperation.RESPONSES:
            continue
        payload: Any = sent.payload
        text = next(
            part["text"] for part in payload["input"][0]["content"] if part["type"] == "input_text"
        )
        try:
            inner = json.loads(text)
        except ValueError:
            continue
        if isinstance(inner, dict) and "item_kinds" in inner:
            found.append(inner)
    return found


async def test_batch_limit_fails_only_that_batch_and_stops_later_calls(monkeypatch) -> None:
    chunks = PythonDocxExamChunker().chunk(content=_exam_bytes())
    anchors = [chunk.anchor for chunk in chunks]
    script = _DoorScript(grouping=_grouping_for(anchors), refuse_batch_calls=(2,))
    outcome, _ = await _convert_with(script, monkeypatch, course_key="SVESVE02")

    assert outcome.ai_limit is AiDailyLimit.POOL
    assert outcome.result.ai_limit is AiDailyLimit.POOL
    assert [event.code for event in outcome.result.events].count("ai_daily_limit") >= 1
    batch_payloads = _sent_batches(script)
    assert len(batch_payloads) == 2, "the first batch and the refused second call; the rest stop"
    sent_anchors = {
        anchor
        for payload in batch_payloads
        for question in payload["questions"]
        for anchor in question
    }
    assert anchors[3] not in sent_anchors, "the third batch makes no door call"
    question_anchors = set(anchors[1:])
    converted = [item for item in outcome.result.document.items if not item.review.reasons]
    assert {item.source_anchor for item in converted} == {anchors[1]}, "the finished batch is kept"
    review_anchors = {
        item.source_anchor for item in outcome.result.document.items if item.review.reasons
    }
    assert set(anchors[2:]) <= review_anchors, "the refused batch items carry review reasons"
    assert question_anchors <= {item.source_anchor for item in outcome.result.document.items}
    assert outcome.update.pending == ()


async def test_content_limit_keeps_the_conversion_and_records_the_limit(monkeypatch) -> None:
    chunks = PythonDocxExamChunker().chunk(content=_exam_bytes())
    script = _DoorScript(grouping=_grouping_for([c.anchor for c in chunks]), refuse_content=True)
    outcome, _ = await _convert_with(script, monkeypatch, course_key="SVESVE02")

    assert outcome.ai_limit is AiDailyLimit.USER_SHARE
    assert outcome.result.document.items, "the conversion completes instead of crashing"
    assert outcome.result.document.header.tags == ()
    decisions = [s for s in script.door.sent if s.operation is DoorOperation.DECISIONS]
    assert decisions, "the first pass still ran before the content refusal"


async def test_grouping_limit_fails_all_pending_with_ai_limit(monkeypatch) -> None:
    chunks = PythonDocxExamChunker().chunk(content=_exam_bytes())
    script = _DoorScript(grouping=_grouping_for([c.anchor for c in chunks]), refuse_grouping=True)
    outcome, _ = await _convert_with(script, monkeypatch)

    assert outcome.ai_limit is AiDailyLimit.POOL
    assert script.door.sent and len(script.door.sent) == 1, "grouping is never retried"
    assert [(e.stage, e.code) for e in outcome.result.events if e.code == "ai_daily_limit"] == [
        ("grouping", "ai_daily_limit")
    ]
    assert outcome.result.document.items, "pending questions become review items"
    assert outcome.update.pending == ()


async def test_overage_under_one_usd_finishes_without_limit(monkeypatch) -> None:
    chunks = PythonDocxExamChunker().chunk(content=_exam_bytes())
    script = _DoorScript(
        grouping=_grouping_for([c.anchor for c in chunks]), batch_charge_usd_micros=100_000
    )
    outcome, job = await _convert_with(script, monkeypatch, course_key="SVESVE02")

    assert outcome.ai_limit is None
    batch_responses = [s for s in script.door.sent if s.operation is DoorOperation.RESPONSES]
    assert len(batch_responses) == 5, "grouping plus all four batches run"
    assert job.caller.overage_usd_micros == 400_000
    assert outcome.result.document.header.tags, "content tags still land"


async def test_overage_past_one_usd_stops_the_next_call(monkeypatch) -> None:
    chunks = PythonDocxExamChunker().chunk(content=_exam_bytes())
    anchors = [chunk.anchor for chunk in chunks]
    script = _DoorScript(grouping=_grouping_for(anchors), batch_charge_usd_micros=600_000)
    outcome, job = await _convert_with(script, monkeypatch, course_key="SVESVE02")

    assert outcome.ai_limit is AiDailyLimit.POOL
    assert job.caller.overage_usd_micros == 1_200_000
    assert [e.code for e in outcome.result.events].count("ai_overage_cap") >= 1
    batch_payloads = _sent_batches(script)
    assert len(batch_payloads) == 2, "two batches convert; the refused call never reaches the door"
    sent_anchors = {
        anchor
        for payload in batch_payloads
        for question in payload["questions"]
        for anchor in question
    }
    assert anchors[3] not in sent_anchors, "the refused third batch reaches no batch call"
    assert anchors[4] not in sent_anchors, "the fourth batch makes no door call"
    converted = [
        item
        for item in outcome.result.document.items
        if item.source_anchor in anchors[1:] and not item.review.reasons
    ]
    assert len(converted) == 2, "the finished batches are kept, the rest are review"
    assert outcome.update.pending == ()


async def test_started_conversion_finishes_as_overage_then_next_is_refused_at_grouping(
    monkeypatch,
) -> None:
    chunks = PythonDocxExamChunker().chunk(content=_exam_bytes())
    grouping = _grouping_for([c.anchor for c in chunks])
    script = _DoorScript(grouping=grouping, refuse_non_overage_after_first=True)

    first_outcome, first_job = await _convert_with(script, monkeypatch, course_key="SVESVE02")
    assert first_outcome.ai_limit is None
    assert first_outcome.result.document.header.tags, "content tags land as overage"
    assert [s.allow_paid_overage for s in script.door.sent][0] is False
    assert all(s.allow_paid_overage for s in script.door.sent[1:])
    first_sent = len(script.door.sent)

    second_pipeline, second_job = _convert(script, course_key="SVESVE02")
    second_outcome = await second_pipeline.convert(job=second_job)
    assert second_outcome.ai_limit is AiDailyLimit.POOL
    assert len(script.door.sent) == first_sent + 1, "only the refused grouping call"
    assert second_outcome.result.document.items
    assert all(item.review.reasons for item in second_outcome.result.document.items)


class _ScriptedFirstPass(MeteredItemTypeLabelerProtocol):
    provider_profile_id = "scripted-first"

    def __init__(self, result: ItemTypeLabelResult) -> None:
        self._result = result

    def estimate_input_tokens(self, *, request: LabelingRequest) -> int:
        return 1

    async def label(self, *, request: LabelingRequest) -> ItemTypeLabeling:
        return ItemTypeLabeling(results=(self._result,), usage=LabelingUsage(input_tokens=1))


class _RefusedSecondPass(SecondPassItemTypeLabelerProtocol):
    provider_profile_id = "scripted-second"

    def __init__(self, error: Exception) -> None:
        self._error = error

    def estimate_tokens(self, *, item: LabelingItem) -> int:
        return 1

    async def label_one(self, *, job_id, item, caller) -> SecondPassLabel:
        raise self._error


def _escalated(item_id: str = "q1") -> ItemTypeLabelResult:
    return ItemTypeLabelResult(
        item_id=item_id,
        label=ItemTypeLabel.UNRESOLVED,
        probabilities={ItemTypeLabel.SINGLE_CHOICE: 0.5, ItemTypeLabel.UNRESOLVED: 0.4},
        probability=0.5,
        threshold=0.95,
        route=LabelRoute.ESCALATE,
    )


async def test_second_pass_limit_keeps_first_pass_top_label_and_reports() -> None:
    refusal = AiDailyLimitReached(limit=AiDailyLimit.USER_SHARE)
    labeler = TwoPassItemTypeLabeler(
        first_pass=_ScriptedFirstPass(_escalated()),
        second_pass=_RefusedSecondPass(refusal),
    )
    seen: list = []
    request = LabelingRequest(
        job_id=uuid4(),
        items=(LabelingItem(item_id="q1", source_text="text"),),
        caller=fixture_caller(),
    )

    labeling = await labeler.label(request=request, on_limit=seen.append)

    (result,) = labeling.results
    assert result.label is ItemTypeLabel.SINGLE_CHOICE
    assert result.failure_code == "ai_daily_limit"
    assert seen == [refusal]


async def test_second_pass_overage_cap_reports_pool() -> None:
    refusal = AiJobOverageCapReached(overage_usd_micros=2_000_000, cap_usd_micros=1_000_000)
    labeler = TwoPassItemTypeLabeler(
        first_pass=_ScriptedFirstPass(_escalated()),
        second_pass=_RefusedSecondPass(refusal),
    )
    seen: list = []
    request = LabelingRequest(
        job_id=uuid4(),
        items=(LabelingItem(item_id="q1", source_text="text"),),
        caller=fixture_caller(),
    )

    labeling = await labeler.label(request=request, on_limit=seen.append)

    (result,) = labeling.results
    assert result.label is ItemTypeLabel.SINGLE_CHOICE
    assert result.failure_code == "ai_overage_cap"
    assert seen == [refusal]


def _content_job(*, owner_id, status=ExamAnswerKeyEnrichmentJobStatus.RUNNING):
    lineage = uuid4()
    saved = suggestion_document(lineage, suggestion_item(item_id="item_001", sequence=1))
    saved = saved.model_copy(
        update={
            "header": saved.header.model_copy(
                update={"course": ExamCourseChoice(key="SVESVE02", name="Svenska 2")}
            )
        }
    )
    return (
        ExamAnswerKeyEnrichmentJob(
            id=uuid4(),
            source_kind=ExamAnswerKeySourceKind.CONTENT_TAGS,
            owner_user_id=owner_id,
            status=status,
            input_filename="Omprov",
            workspace_lineage_id=lineage,
            workspace_document_revision=saved.revision,
            workspace_course_key="SVESVE02",
            workspace_request_json=saved.model_dump(mode="json"),
            locked_by="content-worker",
            available_at=NOW,
            created_at=NOW,
            updated_at=NOW,
        ),
        saved,
    )


def _content_handler(*, classifier, jobs, users):
    return ProcessExamContentSuggestionsHandler(
        classifier=classifier,
        jobs=jobs,
        users=users,
        uow=FakeUow(),
        clock=FixedClock(NOW),
    )


async def test_content_job_limit_fails_with_the_limit_note() -> None:
    owner_id = uuid4()
    users = UserRepositoryStub()
    users.user = user_with_role(Role.USER, user_id=owner_id)
    jobs = InMemoryEnrichmentJobRepository()
    job, _ = _content_job(owner_id=owner_id)
    await jobs.create(job=job)
    classifier = Mock(spec=ExamContentTagSuggester)
    classifier.suggest = AsyncMock(side_effect=AiDailyLimitReached(limit=AiDailyLimit.USER_SHARE))
    handler = _content_handler(classifier=classifier, jobs=jobs, users=users)

    finished = await handler.handle(job=job)

    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.FAILED
    assert finished.last_error == "ai_daily_limit"
    assert finished.ai_limit is AiDailyLimit.USER_SHARE
    assert classifier.suggest.await_count == 1
    assert content_response(finished).message == _LIMIT_MESSAGE


async def test_content_job_overage_cap_fails_with_pool_limit() -> None:
    owner_id = uuid4()
    users = UserRepositoryStub()
    users.user = user_with_role(Role.USER, user_id=owner_id)
    jobs = InMemoryEnrichmentJobRepository()
    job, _ = _content_job(owner_id=owner_id)
    await jobs.create(job=job)
    classifier = Mock(spec=ExamContentTagSuggester)
    classifier.suggest = AsyncMock(
        side_effect=AiJobOverageCapReached(overage_usd_micros=2_000_000, cap_usd_micros=1_000_000)
    )
    handler = _content_handler(classifier=classifier, jobs=jobs, users=users)

    finished = await handler.handle(job=job)

    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.FAILED
    assert finished.last_error == "ai_overage_cap"
    assert finished.ai_limit is AiDailyLimit.POOL
    assert content_response(finished).message == _LIMIT_MESSAGE


async def test_content_job_without_owner_fails_owner_missing() -> None:
    jobs = InMemoryEnrichmentJobRepository()
    job, _ = _content_job(owner_id=uuid4())
    await jobs.create(job=job)
    classifier = Mock(spec=ExamContentTagSuggester)
    classifier.suggest = AsyncMock()
    handler = _content_handler(classifier=classifier, jobs=jobs, users=UserRepositoryStub())

    finished = await handler.handle(job=job)

    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.FAILED
    assert finished.last_error == "owner_missing"
    classifier.suggest.assert_not_awaited()


async def test_grouping_limit_reaches_the_docx_job_row_with_ai_limit() -> None:
    env = environment()
    env.replay.provider._failures["docx_grouping_1"] = AiDailyLimitReached(limit=AiDailyLimit.POOL)
    running = await claim(env)

    finished = await env.processor.handle(job=running)

    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED
    assert finished.ai_limit is AiDailyLimit.POOL
    assert any(
        event.get("code") == "ai_daily_limit" and event.get("stage") == "grouping"
        for event in finished.diagnostics
    )


async def test_docx_job_handler_maps_an_escaped_refusal_to_limit_not_unexpected() -> None:
    env = environment()
    running = await claim(env)

    class _Raising:
        async def convert(self, *, job, fallback_reason=None):
            raise AiDailyLimitReached(limit=AiDailyLimit.USER_SHARE)

    env.processor._pipeline = _Raising()  # type: ignore[assignment]
    finished = await env.processor.handle(job=running)

    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.FAILED
    assert finished.ai_limit is AiDailyLimit.USER_SHARE
    assert finished.last_error == _LIMIT_MESSAGE
    assert any(event.get("code") == "ai_daily_limit" for event in finished.diagnostics)
    assert not any(event.get("code") == "unexpected_error" for event in finished.diagnostics)


async def test_docx_job_handler_maps_an_escaped_cap_to_overage_cap() -> None:
    env = environment()
    running = await claim(env)

    class _Raising:
        async def convert(self, *, job, fallback_reason=None):
            raise AiJobOverageCapReached(overage_usd_micros=2_000_000, cap_usd_micros=1_000_000)

    env.processor._pipeline = _Raising()  # type: ignore[assignment]
    finished = await env.processor.handle(job=running)

    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.FAILED
    assert finished.ai_limit is AiDailyLimit.POOL
    assert finished.last_error == _LIMIT_MESSAGE
    assert any(event.get("code") == "ai_overage_cap" for event in finished.diagnostics)
