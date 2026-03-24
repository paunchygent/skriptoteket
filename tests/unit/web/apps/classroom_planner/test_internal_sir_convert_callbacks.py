"""Unit coverage for internal Sir Convert callback routes.

Purpose:
    Verify that the canonical shared callback route delegates into the seating
    export webhook handler without carrying any legacy route plumbing.

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
    assert set(handler.handle.await_args.kwargs) == {"headers", "raw_body", "correlation_id"}
