"""Replay conversion recordings with synthetic content replies at the HTTP boundary."""

from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import replace
from uuid import uuid4

import httpx
import pytest

from skriptoteket.application.curated_apps.handlers.exam_workspace_conversion_merge import (
    ConversionProgress,
    first_conversion,
    merge_conversion,
    target_from_update,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_run import DocxConversionJob
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_serial_uow import (
    SerializedUnitOfWork,
)
from skriptoteket.config import Settings
from skriptoteket.di.docx_conversion import build_docx_conversion_pipeline
from skriptoteket.domain.curated_apps.exam_workspace.exam_content_tags import (
    ExamContentItem,
    NativeExamContentTag,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import ExamCourseChoice
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import (
    NoSleep,
    NoTransaction,
    RecordingProgress,
    ReplayProvider,
    corpus_chunks,
    corpus_docx,
    decisions_client,
)
from tests.unit.application.curated_apps.handlers.exam_workspace_conversion_support import (
    choice,
    conversion_update,
    placeholder,
)
from tests.unit.llm_door_fakes import fixture_caller

pytestmark = pytest.mark.unit
_EXAM = "chapter_4_poetry_and_lyrics_quiz_med_facit"
_CONTENT = (ExamContentItem(id="SVESVE02:poesi", text="Skönlitterära verkningsmedel."),)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "outcome", ["success", "failure", "pending", "cancelled", "unknown_course"]
)
async def test_conversion_keeps_valid_citations_or_survives_content_failure(
    monkeypatch: pytest.MonkeyPatch,
    outcome: str,
) -> None:
    # The snapshot is an offline input, not a mocked model answer. Only one course is
    # needed here; generator/source completeness is proved separately.
    monkeypatch.setattr(
        "skriptoteket.application.curated_apps.handlers.exam_workspace_docx_pipeline."
        "load_exam_content_catalog",
        lambda: {"SVESVE02": _CONTENT},
    )
    labels = decisions_client(_EXAM)
    requests: list[dict] = []
    classifier_started = asyncio.Event()
    classifier_cancelled = asyncio.Event()

    async def respond(request: httpx.Request) -> httpx.Response:
        sent = json.loads(request.content)
        if sent["questions"][0]["name"].startswith("kind_"):
            return await labels.send(request)
        requests.append(sent)
        if outcome in {"pending", "cancelled"}:
            classifier_started.set()
            try:
                await asyncio.Future()
            finally:
                classifier_cancelled.set()
            raise AssertionError("Pending classifier cannot finish normally")
        if outcome == "failure":
            return httpx.Response(503, json={"error": "synthetic classifier outage"})
        return httpx.Response(
            200,
            json={
                "answers": [
                    {
                        "type": "choice",
                        "name": q["name"],
                        "choice": "c0",
                        "probabilities": [
                            {"value": "c0", "probability": 0.95},
                            {"value": "none", "probability": 0.05},
                        ],
                    }
                    for q in sent["questions"]
                ],
                "usage": {"input_tokens": 91},
            },
        )

    progress = RecordingProgress()
    provider = ReplayProvider(_EXAM)
    async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
        pipeline = build_docx_conversion_pipeline(
            client=client,
            provider=provider,
            sleeper=NoSleep(),
            uow=SerializedUnitOfWork(NoTransaction()),
            settings=Settings.model_construct(
                LLM_ANSWER_KEY_ENABLED=True,
                OPENAI_LLM_ANSWER_KEY_API_KEY="replay-key",
                LLM_DOCX_BATCH_FAMILIES=16,
            ),
            progress=progress,
        )
        source = corpus_docx(_EXAM)
        job = DocxConversionJob(
            job_id=uuid4(),
            worker_id="content-replay",
            document_id=uuid4(),
            filename=f"{_EXAM}.docx",
            source_sha256=hashlib.sha256(source).hexdigest(),
            source_docx=source,
            chunks=corpus_chunks(_EXAM),
            course_key=None if outcome == "unknown_course" else "SVESVE02",
            caller=fixture_caller(),
        )
        conversion = asyncio.create_task(pipeline.convert(job=job))
        if outcome == "cancelled":
            await asyncio.wait_for(classifier_started.wait(), timeout=5)
            conversion.cancel()
            with pytest.raises(asyncio.CancelledError):
                await conversion
            assert classifier_cancelled.is_set(), "Cancellation must join optional work"
            await labels.aclose()
            return
        # This deadline is only a deadlock watchdog. The classifier never returns;
        # cancellation/completion signals, not elapsed time, establish independence.
        result = await asyncio.wait_for(conversion, timeout=5)
        if outcome == "pending":
            assert classifier_started.is_set()
            assert classifier_cancelled.is_set(), "Completed conversion must clean up suggestions"
    await labels.aclose()

    document = result.result.document
    assert document.items, "Classifier failure must not discard the converted exam"
    assert len(document.items) == 28
    assert result.update.document == document
    tags = document.header.tags
    if outcome == "success":
        assert len(requests) == 1
        assert len(tags) == 1
        assert tags[0].id == _CONTENT[0].id
        assert tags[0].origin == "suggested"
        assert tags[0].question_ids
        assert set(tags[0].question_ids) <= {item.item_id for item in document.items}
    else:
        assert tags == ()
        assert len(requests) == (0 if outcome == "unknown_course" else 1)


@pytest.mark.parametrize("teacher_header", [False, True])
@pytest.mark.parametrize("deleted", [False, True])
def test_saved_merge_citations_follow_split_questions_not_assembled_positions(
    teacher_header: bool, deleted: bool
) -> None:
    first = first_conversion(
        update=conversion_update(
            [
                ("q1", [choice("a", "One")]),
                ("q2", [placeholder("b", "Two")]),
                ("q3", [choice("c", "Three")]),
            ],
            pending=("q2",),
        ),
        progress=ConversionProgress.from_question_ids(("q1", "q2", "q3")),
    )
    head = first.document
    if deleted:
        head = head.model_copy(update={"items": head.items[:2]})
    course = ExamCourseChoice(key="course", name="Course")
    teacher_tag = NativeExamContentTag(
        id="course:teacher",
        text="Keep this selection",
        origin="teacher",
        question_ids=("item_001",),
    )
    if teacher_header:
        head = head.model_copy(
            update={
                "header": head.header.model_copy(update={"course": course, "tags": (teacher_tag,)})
            }
        )
    final = conversion_update(
        [
            ("q1", [choice("a", "One")]),
            ("q2", [choice("b", "Two a"), choice("bb", "Two b")]),
            ("q3", [choice("c", "Three")]),
        ],
        pending=(),
    )
    tag = NativeExamContentTag(
        id="course:content",
        text="Content",
        origin="suggested",
        question_ids=("item_002", "item_003", "item_004"),
    )
    target = target_from_update(final)
    target = replace(
        target, header=final.document.header.model_copy(update={"course": course, "tags": (tag,)})
    )
    merged = merge_conversion(head=head, progress=first.progress, target=target)
    if teacher_header:
        assert merged.document.header.tags == (teacher_tag,)
    else:
        expected = ("item_002", "item_1001") + (() if deleted else ("item_003",))
        assert merged.document.header.tags == (tag.model_copy(update={"question_ids": expected}),)
        # Redelivery must recognize its own remapped header rather than treating it
        # as a teacher edit and reintroducing target-local IDs.
        again = merge_conversion(head=merged.document, progress=merged.progress, target=target)
        assert again.document.header.tags == merged.document.header.tags
