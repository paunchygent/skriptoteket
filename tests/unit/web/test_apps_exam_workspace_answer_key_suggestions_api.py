"""Route coverage for exam workspace answer-key suggestion routes.

Purpose:
    Prove the new suggestion routes (TASK-SKRIPT-39-04-07) delegate the
    editor-sent request, the per-job status read and the saved-version
    lookup (TASK-SKRIPT-39-04-09) to their handlers, and
    that the deleted whole-head enrichment routes no longer exist.

Relationships:
    - Covers `web.api.v1.apps_conversion_hub_exam_workspace_enrichment`.
    - Handler behavior is covered in
      `test_exam_workspace_enrichment` (application handlers).

The routes are called directly: FastAPI registration returns the route
function unchanged, so mypy checks every argument below against the
production route signatures and the handler/registry protocols they
declare. The capturing doubles implement those production protocols.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from skriptoteket.application.curated_apps.exam_workspace import (
    ExamWorkspaceAnswerKeySuggestionsResponse,
    ExamWorkspaceEnrichmentState,
    RequestExamWorkspaceAnswerKeySuggestionsRequest,
)
from skriptoteket.domain.curated_apps.models import (
    CuratedAppDefinition,
    CuratedAppPlacement,
    curated_app_tool_id,
)
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.web.api.v1 import apps_conversion_hub_exam_workspace_enrichment as api
from tests.fixtures.identity_fixtures import make_user

pytestmark = pytest.mark.unit


class FakeRegistry:
    """A registry double satisfying `CuratedAppRegistryProtocol`."""

    def __init__(self) -> None:
        self._app = CuratedAppDefinition(
            app_id="documents.conversion_hub",
            tool_id=curated_app_tool_id(app_id="documents.conversion_hub"),
            app_version="app:test",
            title="Conversion Hub",
            min_role=Role.USER,
            placements=[CuratedAppPlacement(profession_slug="larare", category_slug="ovrigt")],
        )

    def list_all(self) -> list[CuratedAppDefinition]:
        return [self._app]

    def get_by_app_id(self, *, app_id: str) -> CuratedAppDefinition | None:
        return self._app if app_id == self._app.app_id else None

    def get_by_tool_id(self, *, tool_id: UUID) -> CuratedAppDefinition | None:
        del tool_id
        return None


class CapturingRequestHandler:
    """A double satisfying `RequestExamWorkspaceAnswerKeySuggestionsHandlerProtocol`."""

    def __init__(self, result: ExamWorkspaceAnswerKeySuggestionsResponse) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    async def handle(
        self,
        *,
        actor: User,
        lineage_id: UUID,
        request: RequestExamWorkspaceAnswerKeySuggestionsRequest,
    ) -> ExamWorkspaceAnswerKeySuggestionsResponse:
        self.calls.append({"actor": actor, "lineage_id": lineage_id, "request": request})
        return self.result


class CapturingStatusHandler:
    """A double satisfying `GetExamWorkspaceAnswerKeySuggestionsStatusHandlerProtocol`."""

    def __init__(self, result: ExamWorkspaceAnswerKeySuggestionsResponse) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    async def handle(
        self, *, actor: User, lineage_id: UUID, job_id: UUID
    ) -> ExamWorkspaceAnswerKeySuggestionsResponse:
        self.calls.append({"actor": actor, "lineage_id": lineage_id, "job_id": job_id})
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
                        "body": [
                            {
                                "heading_level": None,
                                "segments": [{"kind": "text", "text": "Fråga?", "marks": []}],
                            }
                        ],
                        "choices": [
                            {
                                "choice_id": choice_id,
                                "body": [
                                    {
                                        "heading_level": None,
                                        "segments": [{"kind": "text", "text": text, "marks": []}],
                                    }
                                ],
                            }
                            for choice_id, text in (("choice_001", "Ett"), ("choice_002", "Två"))
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

    response = await api.request_exam_workspace_answer_key_suggestions(
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

    response = await api.get_exam_workspace_answer_key_suggestions(
        lineage_id=lineage_id,
        job_id=job_id,
        registry=FakeRegistry(),
        handler=handler,
        user=user,
    )

    assert response.state is ExamWorkspaceEnrichmentState.RUNNING
    assert handler.calls == [{"actor": user, "lineage_id": lineage_id, "job_id": job_id}]


class CapturingFindHandler:
    """A double satisfying `FindExamWorkspaceAnswerKeySuggestionsHandlerProtocol`."""

    def __init__(self, result: ExamWorkspaceAnswerKeySuggestionsResponse | None) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    async def handle(
        self, *, actor: User, lineage_id: UUID, document_revision: int
    ) -> ExamWorkspaceAnswerKeySuggestionsResponse | None:
        self.calls.append(
            {"actor": actor, "lineage_id": lineage_id, "document_revision": document_revision}
        )
        return self.result


@pytest.mark.parametrize("found", [True, False])
async def test_find_route_delegates_the_saved_version_lookup(found: bool) -> None:
    lineage_id = uuid4()
    user = make_user()
    result = (
        ExamWorkspaceAnswerKeySuggestionsResponse(
            job_id=uuid4(),
            lineage_id=lineage_id,
            state=ExamWorkspaceEnrichmentState.QUEUED,
        )
        if found
        else None
    )
    handler = CapturingFindHandler(result)

    response = await api.find_exam_workspace_answer_key_suggestions(
        lineage_id=lineage_id,
        registry=FakeRegistry(),
        handler=handler,
        document_revision=4,
        user=user,
    )

    assert response is result
    assert handler.calls == [{"actor": user, "lineage_id": lineage_id, "document_revision": 4}]


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
