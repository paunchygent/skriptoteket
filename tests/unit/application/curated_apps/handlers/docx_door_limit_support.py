"""Shared door-limit builders for the split DOCX door-limit tests (TASK-SKRIPT-41-01-03 B3).

One synthetic three-question exam served at the door seam with scripted charges and
refusals, plus the content-suggestion job builders. Split by responsibility:
- test_exam_workspace_docx_pipeline_door_limits: pipeline limit scenarios;
- test_exam_workspace_docx_second_pass_door_limits: second-pass scenarios;
- test_exam_workspace_content_suggestion_door_limits: content-suggestion job;
- test_exam_workspace_docx_job_door_limits: DOCX job persistence.
"""

from __future__ import annotations

import io
import json
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

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
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_run import (
    DocxConversionJob,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_serial_uow import (
    SerializedUnitOfWork,
)
from skriptoteket.config import Settings
from skriptoteket.di.docx_conversion import build_docx_conversion_pipeline
from skriptoteket.domain.curated_apps.exam_workspace.exam_content_tags import ExamContentItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import ExamCourseChoice
from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.llm_door import AiDailyLimit, AiDailyLimitReached, AiDoorBusy
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_chunker import (  # noqa: E501
    PythonDocxExamChunker,
)
from skriptoteket.infrastructure.llm.openai.answer_key_structured_provider import (
    OpenAIAnswerKeyStructuredProvider,
)
from skriptoteket.protocols.item_type_labeler import ItemTypeLabel
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
    sse_reply,
    user_with_role,
)

if TYPE_CHECKING:
    import pytest

_CONTENT: tuple[ExamContentItem, ...] = (
    ExamContentItem(id="course:bullet", text="Centralt innehåll"),
)


def exam_bytes() -> bytes:
    document = Document()
    document.add_paragraph("Limit exam", style="Title")
    document.add_paragraph("1. First question.")
    document.add_paragraph("2. Second question.")
    document.add_paragraph("3. Third question.")
    document.add_paragraph("4. Fourth question.")
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def grouping_for(anchors: list[str]) -> dict[str, JsonValue]:
    return {
        "title_anchors": [anchor for anchor in anchors[:1]],
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


def free_text_answer(name: str) -> dict[str, JsonValue]:
    return {
        "type": "choice",
        "name": name,
        "choice": "free_text",
        "probabilities": [
            {
                "value": label.value,
                "probability": 1.0 if label is ItemTypeLabel.FREE_TEXT else 0.0,
            }
            for label in ItemTypeLabel
        ],
    }


def converted_item(anchors: list[str], index: int) -> dict[str, JsonValue]:
    return {
        "source_anchors": [anchor for anchor in anchors],
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


def responses_envelope(content: JsonValue) -> JsonValue:
    return {
        "status": "completed",
        "output_text": json.dumps(content),
        "usage": {"input_tokens": 10, "output_tokens": 10},
    }


def _responses_reply(
    sent: DoorSent, content: JsonValue, *, overage_usd_micros: int | None = None
) -> DoorReply:
    """Serve the requested wire format with the same scripted content and settled charge."""
    response = responses_envelope(content)
    if sent.payload.get("stream") is not True:
        return json_reply(response, overage_usd_micros=overage_usd_micros)
    return sse_reply(
        [
            (
                "response.output_text.delta",
                {"type": "response.output_text.delta", "delta": json.dumps(content)},
            ),
            ("response.completed", {"type": "response.completed", "response": response}),
            (
                "huleedu.door.charge",
                {
                    "type": "huleedu.door.charge",
                    "charge_kind": "overage" if overage_usd_micros is not None else "complimentary",
                    "charge_usd_micros": overage_usd_micros or 0,
                },
            ),
        ]
    )


def anchor_list(raw: object) -> list[str]:
    """The anchor strings of one batch payload question, failing loudly on any other shape."""
    assert isinstance(raw, list)
    anchors: list[str] = []
    for anchor in raw:
        assert isinstance(anchor, str)
        anchors.append(anchor)
    return anchors


def batch_anchors(payload: dict[str, JsonValue]) -> list[list[str]]:
    """The anchor list of every question in one batch request body."""
    raw_questions = payload.get("questions")
    assert isinstance(raw_questions, list)
    return [anchor_list(raw) for raw in raw_questions]


def door_texts(parts: object) -> str:
    """The first input-text part of a Responses payload, failing loudly on any other shape."""
    assert isinstance(parts, list)
    for part in parts:
        assert isinstance(part, dict)
        if part.get("type") != "input_text":
            continue
        text = part.get("text")
        assert isinstance(text, str)
        return text
    raise AssertionError("no input_text part in the Responses payload")


def door_question_names(sent: DoorSent) -> list[str]:
    """The question names of a Decisions payload, failing loudly on any other shape."""
    questions = sent.payload.get("questions")
    assert isinstance(questions, list)
    names: list[str] = []
    for question in questions:
        assert isinstance(question, dict)
        name = question.get("name")
        assert isinstance(name, str)
        names.append(name)
    return names


class DoorScript:
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
        busy_grouping: bool = False,
        busy_batch_calls: tuple[int, ...] = (),
        busy_content: bool = False,
    ) -> None:
        self._grouping = grouping
        self._batch_charge = batch_charge_usd_micros
        self._refuse_grouping = refuse_grouping
        self._refuse_batch_calls = refuse_batch_calls
        self._refuse_content = refuse_content
        self._refuse_non_overage_after_first = refuse_non_overage_after_first
        self._busy_grouping = busy_grouping
        self._busy_batch_calls = busy_batch_calls
        self._busy_content = busy_content
        self.calls = 0
        self.batch_calls = 0
        self.door = RecordingDoor(self.respond)

    def respond(self, sent: DoorSent) -> DoorReply:
        self.calls += 1
        if self._refuse_non_overage_after_first and not sent.allow_paid_overage and self.calls > 1:
            raise AiDailyLimitReached(limit=AiDailyLimit.POOL)
        if sent.operation is DoorOperation.DECISIONS:
            names = door_question_names(sent)
            if names[0].startswith("kind_"):
                return json_reply({"answers": [free_text_answer(name) for name in names]})
            if self._refuse_content:
                raise AiDailyLimitReached(limit=AiDailyLimit.USER_SHARE)
            if self._busy_content:
                raise AiDoorBusy(retry_after_seconds=1)
            return json_reply(
                {
                    "answers": [
                        {
                            "type": "choice",
                            "name": name,
                            "choice": "c0",
                            "probabilities": [
                                {"value": "c0", "probability": 0.9},
                                {"value": "none", "probability": 0.1},
                            ],
                        }
                        for name in names
                    ],
                    "usage": {"input_tokens": 9},
                }
            )
        payload = sent.payload
        raw_input = payload.get("input")
        assert isinstance(raw_input, list)
        first_input = raw_input[0]
        assert isinstance(first_input, dict)
        text = door_texts(first_input.get("content"))
        try:
            inner = json.loads(text)
        except ValueError:
            inner = None
        if isinstance(inner, dict) and "item_kinds" in inner:
            self.batch_calls += 1
            if self.batch_calls in self._refuse_batch_calls:
                raise AiDailyLimitReached(limit=AiDailyLimit.POOL)
            if self.batch_calls in self._busy_batch_calls:
                raise AiDoorBusy(retry_after_seconds=6)
            raw_questions = inner.get("questions")
            assert isinstance(raw_questions, list)
            converted: JsonValue = [
                converted_item(anchor_list(raw), index)
                for index, raw in enumerate(raw_questions, start=1)
            ]
            return _responses_reply(
                sent,
                {
                    "title": None,
                    "instructions": [],
                    "answer_key_anchors": [],
                    "items": converted,
                },
                overage_usd_micros=self._batch_charge or None,
            )
        if self._refuse_grouping:
            raise AiDailyLimitReached(limit=AiDailyLimit.POOL)
        if self._busy_grouping:
            raise AiDoorBusy(retry_after_seconds=None)
        return _responses_reply(sent, self._grouping)


def convert(script: DoorScript, *, course_key: str | None = None):
    from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import (
        RecordingProgress as _Progress,
    )

    content = exam_bytes()
    chunks = PythonDocxExamChunker().chunk(content=content).chunks
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


async def convert_with(script: DoorScript, monkeypatch: pytest.MonkeyPatch, *, course_key=None):
    monkeypatch.setattr(
        "skriptoteket.application.curated_apps.handlers.exam_workspace_docx_content_suggest."
        "load_exam_content_catalog",
        lambda: {"SVESVE02": _CONTENT},
    )
    pipeline, job = convert(script, course_key=course_key)
    outcome = await pipeline.convert(job=job)
    return outcome, job


def sent_batches(script: DoorScript) -> list[dict[str, JsonValue]]:
    """The batch request bodies sent, in order; grouping prose is not JSON."""
    found: list[dict[str, JsonValue]] = []
    for sent in script.door.sent:
        if sent.operation is not DoorOperation.RESPONSES:
            continue
        raw_input = sent.payload.get("input")
        assert isinstance(raw_input, list)
        first_input = raw_input[0]
        assert isinstance(first_input, dict)
        text = door_texts(first_input.get("content"))
        try:
            inner = json.loads(text)
        except ValueError:
            continue
        if isinstance(inner, dict) and "item_kinds" in inner:
            found.append(inner)
    return found


def content_job(*, owner_id: UUID, status=ExamAnswerKeyEnrichmentJobStatus.RUNNING):
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


def content_handler(*, classifier, jobs, users):
    return ProcessExamContentSuggestionsHandler(
        classifier=classifier,
        jobs=jobs,
        users=users,
        uow=FakeUow(),
        clock=FixedClock(NOW),
    )


def failing_classifier(error: Exception):
    classifier = Mock(spec=ExamContentTagSuggester)
    classifier.suggest = AsyncMock(side_effect=error)
    return classifier


async def run_content_job(*, classifier, owner_id: UUID | None = None):
    """Run one content-suggestion job over in-memory fakes with ``classifier``."""
    resolved_owner = owner_id or uuid4()
    users = UserRepositoryStub()
    users.user = user_with_role(Role.USER, user_id=resolved_owner)
    jobs = InMemoryEnrichmentJobRepository()
    job, _ = content_job(owner_id=resolved_owner)
    await jobs.create(job=job)
    handler = content_handler(classifier=classifier, jobs=jobs, users=users)
    return await handler.handle(job=job)
