"""Admin API for the answer-key daily token-lease balance.

Purpose:
    Give operators a read of the current UTC day's lease balance (allocated,
    spent, remaining, reset time) so exhaustion fail-closes in the answer-key
    lane are observable. No teacher-facing surface exists for this.

Relationships:
    Gated by ``require_app_admin_api``; served by
    ``application.curated_apps.handlers.exam_answer_key_lease_status``.
"""

from datetime import date, datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_token_lease import (
    lease_reset_time,
)
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.exam_answer_key import AnswerKeyLeaseStatusHandlerProtocol
from skriptoteket.web.auth.huleedu_app_projection import require_app_admin_api
from skriptoteket.web.dishka_dependencies import FromDishka

router = APIRouter(prefix="/api/v1", tags=["admin-answer-key-lease"])


class AnswerKeyLeaseStatusResponse(BaseModel):
    """Current UTC day's non-refundable answer-key lease balance."""

    model_config = ConfigDict(frozen=True)

    utc_day: date
    allocated_tokens: int
    spent_tokens: int
    available_tokens: int
    resets_at: datetime


@router.get(
    "/admin/answer-key-lease/status",
    response_model=AnswerKeyLeaseStatusResponse,
)
async def get_answer_key_lease_status(
    handler: FromDishka[AnswerKeyLeaseStatusHandlerProtocol],
    user: User = Depends(require_app_admin_api),
) -> AnswerKeyLeaseStatusResponse:
    usage = await handler.handle(actor=user)
    return AnswerKeyLeaseStatusResponse(
        utc_day=usage.utc_day,
        allocated_tokens=usage.daily_token_limit,
        spent_tokens=usage.charged_tokens,
        available_tokens=usage.available_tokens,
        resets_at=lease_reset_time(usage.utc_day),
    )
