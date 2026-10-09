"""Exam workspace answer-key enrichment routes (TASK-SKRIPT-39-04-01).

Purpose:
  Start one advisory machine answer-key enrichment job for the head
  revision of a native exam workspace document, and read its status plus
  the MACHINE_PROPOSED prefill proposals once finished. Proposals stay
  behind teacher review; they are never applied to a saved revision.

Relationships:
  - Shares Conversion Hub app access with `apps_conversion_hub_exam_workspace`.
  - Delegates behavior to `exam_workspace_enrichment` application handlers;
    jobs ride the existing `exam_answer_key_enrichment_jobs` worker lane.
"""

from uuid import UUID

from fastapi import APIRouter, Depends

from skriptoteket.application.curated_apps.handlers.exam_workspace_documents import (
    GetExamWorkspaceDocumentHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_enrichment import (
    NOT_ELIGIBLE_MESSAGE,
    EnqueueExamWorkspaceEnrichmentHandler,
    ExamWorkspaceEnrichmentState,
    ExamWorkspaceEnrichmentStatusResponse,
    GetExamWorkspaceEnrichmentStatusHandler,
)
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.web.api.v1.apps_conversion_hub_access import (
    APP_ID,
    require_conversion_hub_access,
)
from skriptoteket.web.auth.huleedu_app_projection import require_app_user_api
from skriptoteket.web.dishka_dependencies import FromDishka

router = APIRouter(prefix=f"/api/v1/apps/{APP_ID}", tags=["apps"])


@router.post(
    "/exam-workspace/documents/{lineage_id}/enrichment",
    response_model=ExamWorkspaceEnrichmentStatusResponse,
)
async def start_exam_workspace_enrichment(
    lineage_id: UUID,
    registry: FromDishka[CuratedAppRegistryProtocol],
    documents: FromDishka[GetExamWorkspaceDocumentHandler],
    enqueue: FromDishka[EnqueueExamWorkspaceEnrichmentHandler],
    status: FromDishka[GetExamWorkspaceEnrichmentStatusHandler],
    user: User = Depends(require_app_user_api),
) -> ExamWorkspaceEnrichmentStatusResponse:
    """Start enrichment for the head revision, idempotent per revision."""

    require_conversion_hub_access(registry=registry, user=user)
    document_response = await documents.handle(actor=user, lineage_id=lineage_id)
    enqueued = await enqueue.handle(actor=user, document=document_response.document)
    response = await status.handle(actor=user, lineage_id=lineage_id)
    if not enqueued and response.state is ExamWorkspaceEnrichmentState.NOT_REQUESTED:
        return response.model_copy(
            update={
                "state": ExamWorkspaceEnrichmentState.NOT_ELIGIBLE,
                "message": NOT_ELIGIBLE_MESSAGE,
            }
        )
    return response


@router.get(
    "/exam-workspace/documents/{lineage_id}/enrichment",
    response_model=ExamWorkspaceEnrichmentStatusResponse,
)
async def get_exam_workspace_enrichment(
    lineage_id: UUID,
    registry: FromDishka[CuratedAppRegistryProtocol],
    status: FromDishka[GetExamWorkspaceEnrichmentStatusHandler],
    user: User = Depends(require_app_user_api),
) -> ExamWorkspaceEnrichmentStatusResponse:
    """Read enrichment status and proposals for the head revision."""

    require_conversion_hub_access(registry=registry, user=user)
    return await status.handle(actor=user, lineage_id=lineage_id)
