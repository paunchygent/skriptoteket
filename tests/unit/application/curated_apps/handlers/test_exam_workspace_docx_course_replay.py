"""Replay actual v14 batches through the persisted import job and document readback."""

import pytest

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJobStatus,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import ExamCourseChoice
from tests.unit.application.curated_apps.handlers.test_exam_workspace_docx_jobs import (
    claim,
    environment,
)


@pytest.mark.asyncio
@pytest.mark.parametrize("enabled", [True, False])
async def test_picked_course_reaches_every_published_header_and_saved_document(
    enabled: bool,
) -> None:
    env = environment(enabled=enabled)
    running = await claim(env)
    running = running.model_copy(update={"workspace_course_key": "SVESVE02"})
    env.jobs.jobs[running.id] = running

    finished = await env.processor.handle(job=running)

    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED
    expected = ExamCourseChoice(key="SVESVE02", name="Svenska 2")
    if enabled:
        assert env.replay.progress.updates  # Provisional publication is part of this proof.
    assert env.replay.progress.finals
    for update in (*env.replay.progress.updates, *env.replay.progress.finals):
        assert update.document.header.course == expected
    assert running.workspace_lineage_id is not None
    opened = await env.get_handler.handle(actor=env.actor, lineage_id=running.workspace_lineage_id)
    assert opened.document.header.course == expected
    assert opened.document.schema_version == "native_exam_document_v5"
    if enabled:
        assert len(opened.document.items) == 28
