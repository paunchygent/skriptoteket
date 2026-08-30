"""Exam Converter correction-session API routes.

Purpose:
  Expose Skriptoteket-owned durable correction-session read, replacement, and revert
  behavior for authenticated Conversion Hub Exam Converter jobs.

Relationships:
  - Shares Conversion Hub app access with `apps_conversion_hub`.
  - Delegates correction-session behavior to PR-0334 application handlers.
  - Does not call Sir Convert replay or artifact readiness surfaces.
"""

from uuid import UUID

from fastapi import APIRouter, Depends

from skriptoteket.application.curated_apps.exam_converter_correction_sessions import (
    ExamConverterCorrectionSessionResponse,
    ReplaceExamConverterCorrectionIntentsRequest,
    RevertExamConverterCorrectionIntentRequest,
)
from skriptoteket.application.curated_apps.handlers.exam_converter_correction_sessions import (
    GetExamConverterCorrectionSessionHandler,
    ReplaceExamConverterCorrectionIntentsHandler,
    RevertExamConverterCorrectionIntentHandler,
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


@router.get(
    "/exam-converter/jobs/{job_id}/correction-session",
    response_model=ExamConverterCorrectionSessionResponse,
)
async def get_exam_converter_correction_session(
    job_id: UUID,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[GetExamConverterCorrectionSessionHandler],
    user: User = Depends(require_app_user_api),
) -> ExamConverterCorrectionSessionResponse:
    require_conversion_hub_access(registry=registry, user=user)
    return await handler.handle(actor=user, job_id=job_id)


@router.put(
    "/exam-converter/jobs/{job_id}/correction-session/intents",
    response_model=ExamConverterCorrectionSessionResponse,
)
async def replace_exam_converter_correction_intents(
    job_id: UUID,
    request: ReplaceExamConverterCorrectionIntentsRequest,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[ReplaceExamConverterCorrectionIntentsHandler],
    user: User = Depends(require_app_user_api),
) -> ExamConverterCorrectionSessionResponse:
    require_conversion_hub_access(registry=registry, user=user)
    return await handler.handle(actor=user, job_id=job_id, request=request)


@router.delete(
    "/exam-converter/jobs/{job_id}/correction-session/intents",
    response_model=ExamConverterCorrectionSessionResponse,
)
async def revert_exam_converter_correction_intent(
    job_id: UUID,
    request: RevertExamConverterCorrectionIntentRequest,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[RevertExamConverterCorrectionIntentHandler],
    user: User = Depends(require_app_user_api),
) -> ExamConverterCorrectionSessionResponse:
    require_conversion_hub_access(registry=registry, user=user)
    return await handler.handle(actor=user, job_id=job_id, request=request)
