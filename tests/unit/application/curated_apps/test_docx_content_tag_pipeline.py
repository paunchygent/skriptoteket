"""Replay conversion recordings with synthetic content replies at the HTTP boundary."""

from __future__ import annotations

import hashlib
import json
from uuid import uuid4

import httpx
import pytest

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_run import DocxConversionJob
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_serial_uow import (
    SerializedUnitOfWork,
)
from skriptoteket.config import Settings
from skriptoteket.di.docx_conversion import build_docx_conversion_pipeline
from skriptoteket.domain.curated_apps.exam_workspace.exam_content_tags import ExamContentItem
from tests.fixtures.time_fixtures import FixedClock
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import (
    _NOW,
    GrantingLeases,
    NoSleep,
    NoTransaction,
    RecordingProgress,
    ReplayProvider,
    corpus_chunks,
    corpus_docx,
    decisions_client,
)

pytestmark = pytest.mark.unit
_EXAM = "chapter_4_poetry_and_lyrics_quiz_med_facit"
_CONTENT = (ExamContentItem(id="SVESVE02:poesi", text="Skönlitterära verkningsmedel."),)


@pytest.mark.asyncio
@pytest.mark.parametrize("outcome", ["success", "failure", "unknown_course"])
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

    async def respond(request: httpx.Request) -> httpx.Response:
        sent = json.loads(request.content)
        if sent["questions"][0]["name"].startswith("kind_"):
            return await labels.send(request)
        requests.append(sent)
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
            leases=GrantingLeases(),
            uow=SerializedUnitOfWork(NoTransaction()),
            clock=FixedClock(_NOW),
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
        )
        result = await pipeline.convert(job=job)
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
