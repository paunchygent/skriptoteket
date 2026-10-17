"""DigiExam fixture projection and source-neutral request eligibility contracts."""

import hashlib
import json
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from skriptoteket.application.curated_apps.exam_conversion_producers import parse_source_exam
from skriptoteket.application.curated_apps.handlers.conversion_hub_jobs import ConversionHubUpload
from skriptoteket.application.curated_apps.handlers.exam_workspace_enrichment import (
    WorkspaceAnswerKeyRequestPayload,
)
from skriptoteket.domain.curated_apps.exam_workspace.answer_key_view import answer_key_item_views
from skriptoteket.domain.curated_apps.exam_workspace.digiexam_import import (
    build_native_exam_from_digiexam,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import NativeExamDocument
from tests.unit.application.curated_apps.handlers.workspace_suggestion_handler_support import (
    SuggestionHandlerHarness,
)

pytestmark = pytest.mark.unit
FIXTURE = Path("tests/fixtures/exam_conversion/real_inputs/1776888013-ak7-lag-och-ratt.dxe")


def imported_document(
    document_id: UUID, *, source_key: bool = False, zero_points: bool = False
) -> NativeExamDocument:
    """Real Åk7 input; optional explicitly synthetic source-key/zero-score variants."""
    content = FIXTURE.read_bytes()
    if source_key or zero_points:
        payload = json.loads(content)
        questions = payload["exams"][0]["questions"]
        if source_key:
            questions[1]["alternatives"][0]["right"] = True
        if zero_points:
            for question in questions:
                question["maxScore"] = 0
        content = json.dumps(payload).encode()
    exam = parse_source_exam(
        upload=ConversionHubUpload(
            filename=FIXTURE.name, file_bytes=content, content_type="application/octet-stream"
        )
    )
    return build_native_exam_from_digiexam(
        exam=exam, document_id=document_id, source_sha256=hashlib.sha256(content).hexdigest()
    ).document


def test_real_ak7_import_projects_exactly_keyless_choice_and_gap_questions():
    document = imported_document(uuid4())
    views = answer_key_item_views(document)
    assert [item.item_id for item in document.items] == [f"item_{i:03d}" for i in range(1, 9)]
    assert [view.item_id for view in views] == [f"item_{i:03d}" for i in range(1, 7)]
    assert [view.kind.value for view in views] == [
        "gap_fill",
        "multi",
        "gap_fill",
        "gap_fill",
        "gap_fill",
        "gap_fill",
    ]
    assert [view.gap_count for view in views] == [10, 0, 4, 5, 10, 7]
    assert all(item.answer_key.origin.value == "absent" for item in document.items[:6])
    assert all(item.points == 0 for item in document.items[6:])


async def test_source_provided_key_is_ineligible_even_when_explicitly_requested():
    harness = SuggestionHandlerHarness()
    document = imported_document(harness.lineage_id, source_key=True)
    assert document.items[1].answer_key.origin.value == "source_provided"
    assert "item_002" not in {view.item_id for view in answer_key_item_views(document)}
    response = await harness.request(document, item_id="item_002")
    assert response.state.value == "not_eligible"
    assert response.job_id is None
    assert harness.jobs.jobs == {}


@pytest.mark.parametrize("zero_points", [False, True])
async def test_imported_requests_deduplicate_only_same_saved_version_and_question_set(zero_points):
    harness = SuggestionHandlerHarness()
    document = imported_document(harness.lineage_id, zero_points=zero_points)
    whole = await harness.request(document)
    repeated = await harness.request(document)
    single = await harness.request(document, item_id="item_002")
    single_repeated = await harness.request(document, item_id="item_002")
    revised = await harness.request(document.model_copy(update={"revision": 2}))
    assert whole.state.value == single.state.value == revised.state.value == "queued"
    assert whole.job_id == repeated.job_id
    assert single.job_id == single_repeated.job_id
    assert len({whole.job_id, single.job_id, revised.job_id}) == 3
    assert len(harness.jobs.jobs) == 3
    assert whole.job_id is not None
    assert single.job_id is not None
    whole_payload = WorkspaceAnswerKeyRequestPayload.model_validate(
        harness.jobs.jobs[whole.job_id].workspace_request_json
    )
    single_payload = WorkspaceAnswerKeyRequestPayload.model_validate(
        harness.jobs.jobs[single.job_id].workspace_request_json
    )
    assert [view.item_id for view in whole_payload.views] == [f"item_{i:03d}" for i in range(1, 7)]
    assert [view.item_id for view in single_payload.views] == ["item_002"]
    assert all(job.source_kind.value == "workspace" for job in harness.jobs.jobs.values())
    if zero_points:
        assert all(item.points == 0 for item in document.items)
