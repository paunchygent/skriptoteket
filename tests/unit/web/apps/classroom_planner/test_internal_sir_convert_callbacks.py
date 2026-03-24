"""Unit coverage for internal Sir Convert callback routes.

Purpose:
    Verify that both the canonical shared callback route and the temporary
    cutover path delegate into the same seating export webhook handler without
    duplicating callback logic.

Relationships:
    - Covers `web.api.v1.internal_sir_convert_callbacks`.
    - Complements application-level webhook dispatch tests.
"""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from starlette.requests import Request

from skriptoteket.application.curated_apps.classroom_planner import (
    CompleteSeatingExportJobFromWebhookHandler,
)
from skriptoteket.web.api.v1 import internal_sir_convert_callbacks as api


def _unwrap_dishka(fn):
    return getattr(fn, "__dishka_orig_func__", fn)


def _request() -> Request:
    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"{}", "more_body": False}

    request = Request({"type": "http", "headers": []}, receive=receive)
    request.state.correlation_id = uuid4()
    return request


@pytest.mark.unit
@pytest.mark.asyncio
async def test_shared_callback_route_delegates_without_job_hint() -> None:
    handler = AsyncMock(spec=CompleteSeatingExportJobFromWebhookHandler)

    response = await _unwrap_dishka(api.receive_seating_export_job_callback)(
        request=_request(),
        handler=handler,
    )

    assert response == {"status": "ok"}
    assert handler.handle.await_args.kwargs["callback_job_id_hint"] is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_cutover_callback_route_passes_job_id_hint() -> None:
    handler = AsyncMock(spec=CompleteSeatingExportJobFromWebhookHandler)
    job_id_hint = uuid4()

    response = await _unwrap_dishka(api.receive_seating_export_job_cutover_callback)(
        job_id=job_id_hint,
        request=_request(),
        handler=handler,
    )

    assert response == {"status": "ok"}
    assert handler.handle.await_args.kwargs["callback_job_id_hint"] == job_id_hint
