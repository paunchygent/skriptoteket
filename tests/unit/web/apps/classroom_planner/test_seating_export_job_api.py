"""Unit coverage for the classroom-planner seating export-job API routes."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from pydantic import ValidationError
from starlette.requests import Request

from skriptoteket.application.curated_apps.classroom_planner import (
    CreateSeatingExportJobHandler,
    DownloadSeatingExportJobHandler,
    GetSeatingExportJobHandler,
    SeatingExportKind,
    SeatingExportLayoutId,
    SeatingExportPaperSize,
)
from skriptoteket.application.curated_apps.classroom_planner.exports import (
    SeatingExportJobResult,
    SeatingExportJobStatus,
    SeatingExportVaultArtifact,
)
from skriptoteket.web.api.v1 import apps_classroom_planner_seating as api
from skriptoteket.web.api.v1.apps_classroom_planner_export_job_contracts import (
    CreateSeatingExportJobRequest,
)
from tests.fixtures.identity_fixtures import make_user


def _unwrap_dishka(fn):
    return getattr(fn, "__dishka_orig_func__", fn)


def _request() -> Request:
    request = Request({"type": "http", "headers": []})
    request.state.correlation_id = uuid4()
    return request


def _job_result() -> SeatingExportJobResult:
    return SeatingExportJobResult(
        job_id=uuid4(),
        draft_id=uuid4(),
        export_kind=SeatingExportKind.PDF,
        layout_id=SeatingExportLayoutId.PRETTY_BRUTALIST_POSTER,
        paper_size=SeatingExportPaperSize.A3_LANDSCAPE,
        status=SeatingExportJobStatus.SUBMITTED,
        created_at=datetime(2026, 3, 24, tzinfo=timezone.utc),
        download_url=None,
        vault_artifact=None,
        error=None,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_seating_export_job_calls_handler_with_explicit_paper_size():
    user = make_user()
    draft_id = uuid4()
    handler = AsyncMock(spec=CreateSeatingExportJobHandler)
    handler.handle.return_value = _job_result()

    result = await _unwrap_dishka(api.create_seating_export_job)(
        draft_id=draft_id,
        request=_request(),
        payload=CreateSeatingExportJobRequest(
            export_kind=SeatingExportKind.PDF,
            layout_id=SeatingExportLayoutId.PRETTY_BRUTALIST_POSTER,
            paper_size=SeatingExportPaperSize.A3_LANDSCAPE,
        ),
        handler=handler,
        user=user,
    )

    assert result.paper_size == SeatingExportPaperSize.A3_LANDSCAPE
    handler.handle.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_seating_export_job_serializes_status_response():
    user = make_user()
    handler = AsyncMock(spec=GetSeatingExportJobHandler)
    handler.handle.return_value = _job_result().model_copy(
        update={"status": SeatingExportJobStatus.PROCESSING}
    )

    result = await _unwrap_dishka(api.get_seating_export_job)(
        job_id=uuid4(),
        request=_request(),
        handler=handler,
        user=user,
    )

    assert result.status == SeatingExportJobStatus.PROCESSING


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_seating_export_job_serializes_saved_vault_artifact():
    user = make_user()
    handler = AsyncMock(spec=GetSeatingExportJobHandler)
    vault_artifact = SeatingExportVaultArtifact(
        file_id=uuid4(),
        name="klassrumskarta-a3.pdf",
        bytes=12345,
        created_at=datetime(2026, 3, 24, tzinfo=timezone.utc),
    )
    handler.handle.return_value = _job_result().model_copy(
        update={
            "status": SeatingExportJobStatus.SUCCEEDED,
            "download_url": "/api/v1/apps/classroom.group-seating-studio/exports/jobs/x/download",
            "vault_artifact": vault_artifact,
        }
    )

    result = await _unwrap_dishka(api.get_seating_export_job)(
        job_id=uuid4(),
        request=_request(),
        handler=handler,
        user=user,
    )

    assert result.status == SeatingExportJobStatus.SUCCEEDED
    assert result.vault_artifact is not None
    assert result.vault_artifact.file_id == vault_artifact.file_id
    assert result.vault_artifact.name == "klassrumskarta-a3.pdf"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_download_seating_export_job_returns_pdf_attachment_response():
    user = make_user()
    handler = AsyncMock(spec=DownloadSeatingExportJobHandler)
    handler.handle.return_value = ("klass-7a-a3.pdf", b"%PDF")

    response = await _unwrap_dishka(api.download_seating_export_job)(
        job_id=uuid4(),
        handler=handler,
        user=user,
    )

    assert response.media_type == "application/pdf"
    assert response.headers["Content-Disposition"] == 'attachment; filename="klass-7a-a3.pdf"'
    assert response.body == b"%PDF"


@pytest.mark.unit
def test_create_seating_export_job_request_rejects_unknown_paper_size():
    with pytest.raises(ValidationError):
        CreateSeatingExportJobRequest(
            export_kind=SeatingExportKind.PDF,
            layout_id=SeatingExportLayoutId.PRETTY_BRUTALIST_POSTER,
            paper_size="a5_landscape",
        )
