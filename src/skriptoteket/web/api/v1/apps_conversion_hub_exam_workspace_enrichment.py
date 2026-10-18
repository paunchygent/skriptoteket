"""Exam workspace answer-key suggestion routes (TASK-SKRIPT-39-04-07).

Purpose:
  Request AI answer-key suggestions for the questions exactly as the editor
  shows them — one named question, or every keyed-kind question without a
  key — and read the job's status plus the suggestions that arrived. An exam
  opened again finds the newest job requested on its current saved version
  (TASK-SKRIPT-39-04-09).
  Suggestions are written onto the editor's questions by the editor; they
  are never applied to a saved revision here.

Relationships:
  - Shares Conversion Hub app access with `apps_conversion_hub_exam_workspace`.
  - Delegates behavior to `exam_workspace_enrichment` application handlers;
    jobs ride the existing `exam_answer_key_enrichment_jobs` worker lane.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Query

from skriptoteket.application.curated_apps.exam_workspace import (
    ExamWorkspaceAnswerKeySuggestionsResponse,
    RequestExamWorkspaceAnswerKeySuggestionsRequest,
)
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.exam_workspace import (
    FindExamWorkspaceAnswerKeySuggestionsHandlerProtocol,
    GetExamWorkspaceAnswerKeySuggestionsStatusHandlerProtocol,
    RequestExamWorkspaceAnswerKeySuggestionsHandlerProtocol,
)
from skriptoteket.web.api.v1.apps_conversion_hub_access import (
    APP_ID,
    require_conversion_hub_access,
)
from skriptoteket.web.auth.huleedu_app_projection import require_app_ai_api, require_app_user_api
from skriptoteket.web.dishka_dependencies import FromDishka

router = APIRouter(prefix=f"/api/v1/apps/{APP_ID}", tags=["apps"])


@router.post(
    "/exam-workspace/documents/{lineage_id}/answer-key-suggestions",
    response_model=ExamWorkspaceAnswerKeySuggestionsResponse,
)
async def request_exam_workspace_answer_key_suggestions(
    lineage_id: UUID,
    request: RequestExamWorkspaceAnswerKeySuggestionsRequest,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[RequestExamWorkspaceAnswerKeySuggestionsHandlerProtocol],
    user: User = Depends(require_app_ai_api),
) -> ExamWorkspaceAnswerKeySuggestionsResponse:
    """Start one suggestion job on the editor-sent document content."""

    require_conversion_hub_access(registry=registry, user=user)
    return await handler.handle(actor=user, lineage_id=lineage_id, request=request)


@router.get(
    "/exam-workspace/documents/{lineage_id}/answer-key-suggestions",
    response_model=ExamWorkspaceAnswerKeySuggestionsResponse | None,
)
async def find_exam_workspace_answer_key_suggestions(
    lineage_id: UUID,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[FindExamWorkspaceAnswerKeySuggestionsHandlerProtocol],
    document_revision: int = Query(ge=1),
    user: User = Depends(require_app_user_api),
) -> ExamWorkspaceAnswerKeySuggestionsResponse | None:
    """Find the newest suggestion job requested on this saved version, if any."""

    require_conversion_hub_access(registry=registry, user=user)
    return await handler.handle(
        actor=user, lineage_id=lineage_id, document_revision=document_revision
    )


@router.get(
    "/exam-workspace/documents/{lineage_id}/answer-key-suggestions/{job_id}",
    response_model=ExamWorkspaceAnswerKeySuggestionsResponse,
)
async def get_exam_workspace_answer_key_suggestions(
    lineage_id: UUID,
    job_id: UUID,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[GetExamWorkspaceAnswerKeySuggestionsStatusHandlerProtocol],
    user: User = Depends(require_app_user_api),
) -> ExamWorkspaceAnswerKeySuggestionsResponse:
    """Read one suggestion job's status and its arrived suggestions."""

    require_conversion_hub_access(registry=registry, user=user)
    return await handler.handle(actor=user, lineage_id=lineage_id, job_id=job_id)
