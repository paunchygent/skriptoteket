"""Internal Sir Convert callback routes for curated-app push integrations.

Purpose:
    Expose the canonical internal webhook intake surface that Sir Convert-a-Lot
    calls when async conversion jobs complete, while delegating app-specific
    completion logic to typed handlers.

Relationships:
    - Used by the classroom-planner seating export-job flow in PR-0119.
    - Included by the shared web router alongside public API routes.
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from skriptoteket.application.curated_apps.classroom_planner import (
    CompleteSeatingExportJobFromWebhookHandler,
)
from skriptoteket.web.dishka_compat import FromDishka, inject
from skriptoteket.web.request_metadata import get_correlation_id

router = APIRouter(prefix="/api/v1/internal/sir-convert-a-lot", tags=["internal"])


async def _handle_seating_export_job_callback(
    request: Request,
    handler: CompleteSeatingExportJobFromWebhookHandler,
) -> dict[str, str]:
    """Receive one signed Sir Convert webhook callback for a seating export job."""

    correlation_id_uuid = get_correlation_id(request)
    await handler.handle(
        headers={key: value for key, value in request.headers.items()},
        raw_body=await request.body(),
        correlation_id=str(correlation_id_uuid) if correlation_id_uuid is not None else None,
    )
    return {"status": "ok"}


@router.post("/classroom-planner/seating-export-jobs")
@inject
async def receive_seating_export_job_callback(
    request: Request,
    handler: FromDishka[CompleteSeatingExportJobFromWebhookHandler],
) -> dict[str, str]:
    """Receive the canonical shared seating export callback."""

    return await _handle_seating_export_job_callback(request, handler)
