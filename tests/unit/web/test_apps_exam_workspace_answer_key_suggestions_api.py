"""Route coverage for exam workspace answer-key suggestion routes.

Purpose:
    Prove the new suggestion routes (TASK-SKRIPT-39-04-07) delegate the
    editor-sent request and the per-job status read to their handlers, and
    that the deleted whole-head enrichment routes no longer exist.

Relationships:
    - Covers `web.api.v1.apps_conversion_hub_exam_workspace_enrichment`.
    - Handler behavior is covered in
      `test_exam_workspace_enrichment` (application handlers).
"""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.exam_workspace import (
    ExamWorkspaceAnswerKeySuggestionsResponse,
    ExamWorkspaceEnrichmentState,
    RequestExamWorkspaceAnswerKeySuggestionsRequest,
)
from skriptoteket.domain.identity.models import Role
from skriptoteket.web.api.v1 import apps_conversion_hub_exam_workspace_enrichment as api
from tests.fixtures.identity_fixtures import make_user

pytestmark = pytest.mark.unit


def _unwrap_dishka(fn: object) -> object:
    return getattr(fn, "__dishka_orig_func__", fn)


class FakeRegistry:
    def get_by_app_id(self, *, app_id: str) -> SimpleNamespace:
        del app_id
        return SimpleNamespace(app_id="documents.conversion_hub", min_role=Role.USER)


class CapturingRequestHandler:
    def __init__(self, result: ExamWorkspaceAnswerKeySuggestionsResponse) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    async def handle(self, **kwargs: object) -> ExamWorkspaceAnswerKeySuggestionsResponse:
        self.calls.append(kwargs)
        return self.result


class CapturingStatusHandler:
    def __init__(self, result: ExamWorkspaceAnswerKeySuggestionsResponse) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    async def handle(self, **kwargs: object) -> ExamWorkspaceAnswerKeySuggestionsResponse:
        self.calls.append(kwargs)
        return self.result


async def test_request_route_delegates_the_editor_sent_document() -> None:
    lineage_id = uuid4()
    job_id = uuid4()
    user = make_user()
    handler = CapturingRequestHandler(
        ExamWorkspaceAnswerKeySuggestionsResponse(
            job_id=job_id,
            lineage_id=lineage_id,
            state=ExamWorkspaceEnrichmentState.QUEUED,
        )
    )
    request = RequestExamWorkspaceAnswerKeySuggestionsRequest.model_validate(
        {
            "document": {
                "document_id": str(lineage_id),
                "revision": 1,
                "title": "Prov",
                "origin": {"kind": "created"},
                "items": [
                    {
                        "item_id": "item_001",
                        "sequence": 1,
                        "kind": "single_choice",
                        "body": [{"segments": [{"kind": "text", "text": "Fråga?"}]}],
                        "choices": [
                            {"choice_id": "choice_001", "text": "Ett"},
                            {"choice_id": "choice_002", "text": "Två"},
                        ],
                        "answer_key": {"origin": "absent"},
                        "review": {
                            "state": "review_complete",
                            "parse_origin": "teacher_created",
                        },
                    }
                ],
            },
            "item_id": "item_001",
        }
    )

    route = _unwrap_dishka(api.request_exam_workspace_answer_key_suggestions)
    response = await route(  # type: ignore[operator]
        lineage_id=lineage_id,
        request=request,
        registry=FakeRegistry(),
        handler=handler,
        user=user,
    )

    assert response.job_id == job_id
    assert handler.calls == [{"actor": user, "lineage_id": lineage_id, "request": request}]


async def test_status_route_delegates_the_job_read() -> None:
    lineage_id = uuid4()
    job_id = uuid4()
    user = make_user()
    handler = CapturingStatusHandler(
        ExamWorkspaceAnswerKeySuggestionsResponse(
            job_id=job_id,
            lineage_id=lineage_id,
            state=ExamWorkspaceEnrichmentState.RUNNING,
        )
    )

    route = _unwrap_dishka(api.get_exam_workspace_answer_key_suggestions)
    response = await route(  # type: ignore[operator]
        lineage_id=lineage_id,
        job_id=job_id,
        registry=FakeRegistry(),
        handler=handler,
        user=user,
    )

    assert response.state is ExamWorkspaceEnrichmentState.RUNNING
    assert handler.calls == [{"actor": user, "lineage_id": lineage_id, "job_id": job_id}]


def test_router_exposes_only_the_new_suggestion_routes() -> None:
    paths = {str(getattr(route, "path", "")) for route in api.router.routes}

    assert (
        "/api/v1/apps/documents.conversion_hub/exam-workspace/documents/{lineage_id}/answer-key-suggestions"
        in paths
    )
    assert (
        "/api/v1/apps/documents.conversion_hub/exam-workspace/documents/{lineage_id}/answer-key-suggestions/{job_id}"
        in paths
    )
    assert not any(path.endswith("/enrichment") for path in paths)
