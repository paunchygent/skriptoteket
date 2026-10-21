"""Replay actual v14 batches through the persisted import job and document readback."""

import pytest

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJobStatus,
)
from skriptoteket.application.curated_apps.exam_content_tagging import (
    MeteredExamContentTagClassifier,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_content_tags import (
    NativeExamContentTag,
    load_exam_content_catalog,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import ExamCourseChoice
from skriptoteket.protocols.item_type_labeler import ContentTagClassificationRequest
from tests.unit.application.curated_apps.handlers.test_exam_workspace_docx_jobs import (
    claim,
    environment,
)


@pytest.mark.asyncio
@pytest.mark.parametrize("enabled", [True, False])
async def test_picked_course_reaches_every_published_header_and_saved_document(
    enabled: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    content_requests: list[ContentTagClassificationRequest] = []

    async def no_content_tags(
        self: MeteredExamContentTagClassifier,
        *,
        request: ContentTagClassificationRequest,
        fail_open: bool = True,
    ) -> tuple[NativeExamContentTag, ...]:
        content_requests.append(request)
        return ()

    # These live recordings predate content tagging. Stub only that optional
    # lane so it cannot consume the type labeler's recorded Decisions reply.
    monkeypatch.setattr(MeteredExamContentTagClassifier, "suggest", no_content_tags)
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
    assert opened.document.schema_version == "native_exam_document_v11"
    if enabled:
        assert len(opened.document.items) == 28
        assert len(content_requests) == 1
        assert content_requests[0].content_items == load_exam_content_catalog()[expected.key]
    else:
        assert content_requests == []
