"""The disabled-enrichment worker still claims and executes native DigiExam imports."""

from datetime import timedelta
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from dishka import make_async_container

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeySourceKind,
)
from skriptoteket.application.curated_apps.handlers.exam_answer_key_enrichment_jobs import (
    ProcessExamAnswerKeyEnrichmentJobHandler,
)
from skriptoteket.workers.exam_answer_key_enrichment import process_next_answer_key_enrichment_job
from tests.fixtures.time_fixtures import FixedClock
from tests.unit.application.curated_apps.handlers.test_exam_workspace_documents import _NOW
from tests.unit.application.curated_apps.test_exam_workspace_digiexam_job import _environment
from tests.unit.workers.test_exam_answer_key_enrichment import AnswerKeyEnrichmentWorkerProvider


@pytest.mark.asyncio
async def test_dxe_import_runs_when_ai_enrichment_is_disabled():
    env, actor, _, importer, processor = _environment()
    fixture = Path("tests/fixtures/exam_conversion/sanitized-embedded-image.dxe")
    queued = await importer.handle(
        actor=actor, filename=fixture.name, content=fixture.read_bytes(), course_key=None
    )
    dispatch = AsyncMock(spec=ProcessExamAnswerKeyEnrichmentJobHandler)
    dispatch.fail_next_expired.return_value = None
    # Exercise the worker's claim filters and actual import publication; dispatch is its port.
    dispatch.handle.side_effect = processor.handle
    container = make_async_container(
        AnswerKeyEnrichmentWorkerProvider(
            uow=env.store._uow,
            jobs=env.enrichment_jobs,
            handler=dispatch,
        )
    )
    try:
        processed = await process_next_answer_key_enrichment_job(
            container=container,
            worker_id="dxe-disabled-ai",
            now=_NOW,
            lease_ttl=timedelta(minutes=5),
            clock=FixedClock(_NOW),
            enrichment_enabled=False,
        )
    finally:
        await container.close()
    assert processed is True
    dispatch.handle.assert_awaited_once()
    claimed = dispatch.handle.await_args.kwargs["job"]
    assert claimed.id == queued.job_id
    assert claimed.source_kind is ExamAnswerKeySourceKind.DIGIEXAM_IMPORT
    stored = env.enrichment_jobs.jobs[queued.job_id]
    assert stored.status.value == "succeeded"
    assert stored.source_dxe is None
    opened = await env.get_handler.handle(actor=actor, lineage_id=queued.lineage_id)
    assert opened.document.origin.kind == "digiexam_import"
    assert len(opened.document.assets) == 1
