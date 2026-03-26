"""Unit coverage for the classroom-planner grouping export-job API routes."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from pydantic import ValidationError
from starlette.requests import Request

from skriptoteket.application.curated_apps.classroom_planner import (
    CreateGroupingExportJobHandler,
    DownloadGroupingExportJobHandler,
    GetGroupingExportJobHandler,
    GetRecoverableGroupingExportJobForDraftHandler,
    GroupingExportKind,
    GroupingExportPaperSize,
)
from skriptoteket.application.curated_apps.classroom_planner.exports import (
    GroupingExportJobResult,
    GroupingExportJobStatus,
    GroupingExportVaultArtifact,
)
from skriptoteket.web.api.v1 import apps_classroom_planner_grouping as api
from skriptoteket.web.api.v1.apps_classroom_planner_export_job_contracts import (
    CreateGroupingExportJobRequest,
)
from tests.fixtures.identity_fixtures import make_user


def _unwrap_dishka(fn):
    return getattr(fn, "__dishka_orig_func__", fn)


def _request() -> Request:
    request = Request({"type": "http", "headers": []})
    request.state.correlation_id = uuid4()
    return request


def _job_result() -> GroupingExportJobResult:
    return GroupingExportJobResult(
        job_id=uuid4(),
        draft_id=uuid4(),
        export_kind=GroupingExportKind.XLSX,
        paper_size=None,
        status=GroupingExportJobStatus.SUBMITTED,
        created_at=datetime(2026, 3, 26, tzinfo=timezone.utc),
        download_url=None,
        vault_artifact=None,
        error=None,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_grouping_export_job_calls_handler_with_xlsx_payload():
    user = make_user()
    draft_id = uuid4()
    handler = AsyncMock(spec=CreateGroupingExportJobHandler)
    handler.handle.return_value = _job_result()

    result = await _unwrap_dishka(api.create_grouping_export_job)(
        draft_id=draft_id,
        _request=_request(),
        payload=CreateGroupingExportJobRequest(
            export_kind=GroupingExportKind.XLSX,
            paper_size=None,
        ),
        handler=handler,
        user=user,
    )

    assert result.export_kind is GroupingExportKind.XLSX
    assert result.paper_size is None
    handler.handle.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_grouping_export_job_serializes_processing_response():
    user = make_user()
    handler = AsyncMock(spec=GetGroupingExportJobHandler)
    handler.handle.return_value = _job_result().model_copy(
        update={
            "status": GroupingExportJobStatus.PROCESSING,
            "export_kind": GroupingExportKind.PDF,
            "paper_size": GroupingExportPaperSize.A4_PORTRAIT,
        }
    )

    result = await _unwrap_dishka(api.get_grouping_export_job)(
        job_id=uuid4(),
        handler=handler,
        user=user,
    )

    assert result.status is GroupingExportJobStatus.PROCESSING
    assert result.paper_size is GroupingExportPaperSize.A4_PORTRAIT


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_recoverable_grouping_export_job_for_draft_returns_none_when_empty():
    user = make_user()
    handler = AsyncMock(spec=GetRecoverableGroupingExportJobForDraftHandler)
    handler.handle.return_value = None

    result = await _unwrap_dishka(api.get_recoverable_grouping_export_job_for_draft)(
        draft_id=uuid4(),
        handler=handler,
        user=user,
    )

    assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_grouping_export_job_serializes_saved_vault_artifact():
    user = make_user()
    handler = AsyncMock(spec=GetGroupingExportJobHandler)
    vault_artifact = GroupingExportVaultArtifact(
        file_id=uuid4(),
        name="klass-7a-gruppindelning.xlsx",
        bytes=12345,
        created_at=datetime(2026, 3, 26, tzinfo=timezone.utc),
    )
    handler.handle.return_value = _job_result().model_copy(
        update={
            "status": GroupingExportJobStatus.SUCCEEDED,
            "download_url": (
                "/api/v1/apps/classroom.group-seating-studio/grouping/exports/jobs/x/download"
            ),
            "vault_artifact": vault_artifact,
        }
    )

    result = await _unwrap_dishka(api.get_grouping_export_job)(
        job_id=uuid4(),
        handler=handler,
        user=user,
    )

    assert result.status is GroupingExportJobStatus.SUCCEEDED
    assert result.vault_artifact is not None
    assert result.vault_artifact.file_id == vault_artifact.file_id


@pytest.mark.unit
@pytest.mark.asyncio
async def test_download_grouping_export_job_returns_xlsx_attachment_response():
    user = make_user()
    handler = AsyncMock(spec=DownloadGroupingExportJobHandler)
    xlsx_bytes = b"PK\x03\x04"
    handler.handle.return_value = (
        "klass-7a-gruppindelning.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        xlsx_bytes,
    )

    response = await _unwrap_dishka(api.download_grouping_export_job)(
        job_id=uuid4(),
        handler=handler,
        user=user,
    )

    assert (
        response.media_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert response.headers["Content-Disposition"] == (
        'attachment; filename="klass-7a-gruppindelning.xlsx"'
    )
    assert response.body == xlsx_bytes


@pytest.mark.unit
def test_create_grouping_export_job_request_rejects_non_a4_pdf_size():
    with pytest.raises(ValidationError):
        CreateGroupingExportJobRequest(
            export_kind=GroupingExportKind.PDF,
            paper_size="letter_portrait",
        )


@pytest.mark.unit
def test_create_grouping_export_job_request_rejects_xlsx_with_paper_size():
    with pytest.raises(ValidationError):
        CreateGroupingExportJobRequest(
            export_kind=GroupingExportKind.XLSX,
            paper_size=GroupingExportPaperSize.A4_PORTRAIT,
        )
