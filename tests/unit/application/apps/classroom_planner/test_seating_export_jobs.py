"""Behavior tests for classroom-planner seating export jobs."""

from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.classroom_planner import (
    CompleteSeatingExportJobFromWebhookHandler,
    CreateSeatingExportJobHandler,
    DownloadSeatingExportJobHandler,
    GetRecoverableSeatingExportJobForDraftHandler,
    GetSeatingExportJobHandler,
    PrepareSeatingExportHandler,
    SeatingExportJobFinalizer,
    SeatingExportKind,
    SeatingExportLayoutId,
    SeatingExportPaperSize,
)
from skriptoteket.application.curated_apps.classroom_planner.exports import (
    PosterSceneRoom,
    PreparedSeatingExportContract,
    RenderedSeatingPosterBundle,
    SeatingExportJob,
    SeatingExportJobStatus,
    SeatingPosterScene,
)
from skriptoteket.config import Settings
from skriptoteket.domain.scripting.vault import VaultFile, VaultFileSourceKind
from skriptoteket.protocols.classroom_planner_exports import (
    SeatingExportJobRepositoryProtocol,
    SeatingExportWebhookBindingRepositoryProtocol,
    SeatingPosterRendererProtocol,
)
from skriptoteket.protocols.sir_convert_a_lot_v2 import (
    SirConvertALotClientV2Protocol,
    SirConvertSubmittedJobV2,
)
from skriptoteket.protocols.vault import (
    VaultFileRepositoryProtocol,
    VaultStorageProtocol,
    VaultUsageRepositoryProtocol,
)
from tests.fixtures.identity_fixtures import make_user


class _DummyUow:
    async def __aenter__(self) -> _DummyUow:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


class _FixedClock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class _FixedIdGenerator:
    def __init__(self, values: list[object]) -> None:
        self._values = list(values)

    def new_uuid(self):
        return self._values.pop(0)


class _DummyBinding:
    def __init__(
        self,
        *,
        subscription_id: str | None = None,
        callback_url: str | None = None,
        secret: str | None = None,
    ) -> None:
        now = datetime(2026, 3, 24, tzinfo=timezone.utc)
        self.binding_key = "classroom-planner-seating-export"
        self.subscription_id = subscription_id
        self.callback_url = callback_url
        self.secret = secret
        self.created_at = now
        self.updated_at = now

    def model_copy(self, *, update: dict[str, str | None]):
        return _DummyBinding(
            subscription_id=update.get("subscription_id", self.subscription_id),
            callback_url=update.get("callback_url", self.callback_url),
            secret=update.get("secret", self.secret),
        )


def _prepared_contract() -> PreparedSeatingExportContract:
    draft_id = uuid4()
    return PreparedSeatingExportContract(
        seating_draft_id=draft_id,
        roster_id=uuid4(),
        roster_name="Klass 7A",
        template_id=uuid4(),
        template_name="Sal A",
        export_kind=SeatingExportKind.PDF,
        layout_id=SeatingExportLayoutId.PRETTY_BRUTALIST_POSTER,
        poster_scene=SeatingPosterScene(
            room=PosterSceneRoom(grid_cols=14, grid_rows=9),
            seats=[],
            fixtures=[],
        ),
    )


def _job(
    *,
    owner_user_id,
    status: SeatingExportJobStatus,
    vault_file_id=None,
    upstream_job_id="upstream-1",
) -> SeatingExportJob:
    now = datetime(2026, 3, 24, tzinfo=timezone.utc)
    prepared = _prepared_contract()
    return SeatingExportJob(
        id=uuid4(),
        owner_user_id=owner_user_id,
        draft_id=prepared.seating_draft_id,
        roster_id=prepared.roster_id,
        template_id=prepared.template_id,
        export_kind=prepared.export_kind,
        layout_id=prepared.layout_id,
        paper_size=SeatingExportPaperSize.A3_LANDSCAPE,
        output_filename="klass-7a-a3.pdf",
        status=status,
        upstream_job_id=upstream_job_id,
        webhook_subscription_id="whsub-1",
        webhook_secret="whsec-1",
        vault_file_id=vault_file_id,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_seating_export_job_submits_rendered_html_and_css_bundle():
    actor = make_user()
    now = datetime(2026, 3, 24, tzinfo=timezone.utc)
    prepare = AsyncMock(spec=PrepareSeatingExportHandler)
    prepare.handle.return_value = _prepared_contract()
    jobs = AsyncMock(spec=SeatingExportJobRepositoryProtocol)
    bindings = AsyncMock(spec=SeatingExportWebhookBindingRepositoryProtocol)
    renderer = AsyncMock(spec=SeatingPosterRendererProtocol)
    renderer.render.return_value = RenderedSeatingPosterBundle(
        html_filename="index.html",
        html_content="<html><head></head><body>Poster</body></html>",
        css_filename="poster.css",
        css_content="body{color:black;}",
        output_filename="klass-7a-a3.pdf",
    )
    client = AsyncMock(spec=SirConvertALotClientV2Protocol)
    client.create_webhook_subscription.return_value = SimpleNamespace(
        subscription_id="whsub-1",
        callback_url="http://127.0.0.1:8000/api/v1/internal/sir-convert-a-lot/classroom-planner/seating-export-jobs",
        secret="whsec-1",
    )
    client.submit_job.return_value = SirConvertSubmittedJobV2(
        job_id="upstream-1",
        status="queued",
        idempotent_replay=False,
    )
    job_id = uuid4()
    created_job = _job(owner_user_id=actor.id, status=SeatingExportJobStatus.SUBMITTED)
    created_job = created_job.model_copy(
        update={
            "id": job_id,
            "upstream_job_id": None,
            "webhook_subscription_id": None,
            "webhook_secret": None,
        }
    )
    updated_job = created_job.model_copy(
        update={
            "upstream_job_id": "upstream-1",
            "webhook_subscription_id": "whsub-1",
            "webhook_secret": "whsec-1",
        }
    )
    jobs.create.return_value = created_job
    jobs.update.return_value = updated_job
    bindings.get_shared_for_update.return_value = _DummyBinding()
    bindings.update_shared.return_value = _DummyBinding(
        subscription_id="whsub-1",
        callback_url="http://127.0.0.1:8000/api/v1/internal/sir-convert-a-lot/classroom-planner/seating-export-jobs",
        secret="whsec-1",
    )

    handler = CreateSeatingExportJobHandler(
        prepare=prepare,
        jobs=jobs,
        webhook_bindings=bindings,
        renderer=renderer,
        client=client,
        uow=_DummyUow(),
        clock=_FixedClock(now),
        id_generator=_FixedIdGenerator([job_id]),
        settings=Settings(SIR_CONVERT_A_LOT_V2_CALLBACK_BASE_URL="http://127.0.0.1:8000"),
    )

    result = await handler.handle(
        actor=actor,
        draft_id=created_job.draft_id,
        export_kind=SeatingExportKind.PDF,
        layout_id=SeatingExportLayoutId.PRETTY_BRUTALIST_POSTER,
        paper_size=SeatingExportPaperSize.A3_LANDSCAPE,
        correlation_id="corr-1",
    )

    submit_request = client.submit_job.await_args.kwargs["request"]
    assert submit_request.filename == "index.html"
    assert submit_request.resources_filename == "resources.zip"
    assert b"poster.css" in submit_request.resources_bytes
    assert submit_request.job_spec["conversion"]["css_filenames"] == ["poster.css"]
    assert result.status == SeatingExportJobStatus.SUBMITTED


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_seating_export_job_marks_persisted_job_failed_when_webhook_onboarding_fails():
    actor = make_user()
    now = datetime(2026, 3, 24, tzinfo=timezone.utc)
    prepare = AsyncMock(spec=PrepareSeatingExportHandler)
    prepare.handle.return_value = _prepared_contract()
    jobs = AsyncMock(spec=SeatingExportJobRepositoryProtocol)
    bindings = AsyncMock(spec=SeatingExportWebhookBindingRepositoryProtocol)
    renderer = AsyncMock(spec=SeatingPosterRendererProtocol)
    renderer.render.return_value = RenderedSeatingPosterBundle(
        html_filename="index.html",
        html_content="<html><body>Poster</body></html>",
        css_filename="poster.css",
        css_content="body{color:black;}",
        output_filename="klass-7a-a3.pdf",
    )
    client = AsyncMock(spec=SirConvertALotClientV2Protocol)
    client.create_webhook_subscription.side_effect = RuntimeError("webhook down")
    job_id = uuid4()
    created_job = _job(
        owner_user_id=actor.id,
        status=SeatingExportJobStatus.SUBMITTED,
        upstream_job_id=None,
    ).model_copy(
        update={
            "id": job_id,
            "webhook_subscription_id": None,
            "webhook_secret": None,
        }
    )
    failed_job = created_job.model_copy(
        update={
            "status": SeatingExportJobStatus.FAILED,
            "error_message": "Kunde inte starta PDF-exporten just nu. Försök igen.",
        }
    )
    jobs.create.return_value = created_job
    jobs.update.return_value = failed_job
    bindings.get_shared_for_update.return_value = _DummyBinding()

    handler = CreateSeatingExportJobHandler(
        prepare=prepare,
        jobs=jobs,
        webhook_bindings=bindings,
        renderer=renderer,
        client=client,
        uow=_DummyUow(),
        clock=_FixedClock(now),
        id_generator=_FixedIdGenerator([job_id]),
        settings=Settings(SIR_CONVERT_A_LOT_V2_CALLBACK_BASE_URL="http://127.0.0.1:8000"),
    )

    with pytest.raises(RuntimeError, match="webhook down"):
        await handler.handle(
            actor=actor,
            draft_id=created_job.draft_id,
            export_kind=SeatingExportKind.PDF,
            layout_id=SeatingExportLayoutId.PRETTY_BRUTALIST_POSTER,
            paper_size=SeatingExportPaperSize.A3_LANDSCAPE,
            correlation_id="corr-1",
        )

    updated = jobs.update.await_args.kwargs["job"]
    assert updated.status is SeatingExportJobStatus.FAILED
    assert updated.error_message == "Kunde inte starta PDF-exporten just nu. Försök igen."


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_seating_export_job_refreshes_running_status():
    actor = make_user()
    jobs = AsyncMock(spec=SeatingExportJobRepositoryProtocol)
    vault_files = AsyncMock(spec=VaultFileRepositoryProtocol)
    client = AsyncMock(spec=SirConvertALotClientV2Protocol)
    finalizer = AsyncMock(spec=SeatingExportJobFinalizer)
    job = _job(owner_user_id=actor.id, status=SeatingExportJobStatus.SUBMITTED)
    refreshed = job.model_copy(update={"status": SeatingExportJobStatus.PROCESSING})
    jobs.get_by_id.return_value = job
    jobs.update.return_value = refreshed
    client.get_job.return_value = SimpleNamespace(job_id="upstream-1", status="running")
    handler = GetSeatingExportJobHandler(
        jobs=jobs,
        vault_files=vault_files,
        client=client,
        finalizer=finalizer,
        uow=_DummyUow(),
    )

    result = await handler.handle(actor=actor, job_id=job.id, correlation_id="corr-1")

    assert result.status == SeatingExportJobStatus.PROCESSING
    jobs.update.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_seating_export_job_recovers_finished_upstream_job_without_webhook():
    actor = make_user()
    completed_file_id = uuid4()
    jobs = AsyncMock(spec=SeatingExportJobRepositoryProtocol)
    vault_files = AsyncMock(spec=VaultFileRepositoryProtocol)
    client = AsyncMock(spec=SirConvertALotClientV2Protocol)
    finalizer = AsyncMock(spec=SeatingExportJobFinalizer)
    job = _job(owner_user_id=actor.id, status=SeatingExportJobStatus.PROCESSING)
    completed = job.model_copy(
        update={
            "status": SeatingExportJobStatus.SUCCEEDED,
            "vault_file_id": completed_file_id,
        }
    )
    jobs.get_by_id.return_value = job
    vault_files.get_by_id.return_value = VaultFile(
        id=completed_file_id,
        user_id=actor.id,
        name="klass-7a-a3.pdf",
        bytes=12345,
        source_kind=VaultFileSourceKind.APP_EXPORT,
        source_run_id=None,
        source_artifact_id="classroom.group-seating-studio",
        created_at=datetime(2026, 3, 24, tzinfo=timezone.utc),
        deleted_at=None,
    )
    client.get_job.return_value = SimpleNamespace(job_id="upstream-1", status="succeeded")
    finalizer.complete_success.return_value = completed
    handler = GetSeatingExportJobHandler(
        jobs=jobs,
        vault_files=vault_files,
        client=client,
        finalizer=finalizer,
        uow=_DummyUow(),
    )

    result = await handler.handle(actor=actor, job_id=job.id, correlation_id="corr-1")

    assert result.status is SeatingExportJobStatus.SUCCEEDED
    finalizer.complete_success.assert_awaited_once_with(job=job, correlation_id="corr-1")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_recoverable_seating_export_job_for_draft_prefers_in_flight_job() -> None:
    actor = make_user()
    jobs = AsyncMock(spec=SeatingExportJobRepositoryProtocol)
    vault_files = AsyncMock(spec=VaultFileRepositoryProtocol)
    client = AsyncMock(spec=SirConvertALotClientV2Protocol)
    finalizer = AsyncMock(spec=SeatingExportJobFinalizer)
    in_flight_job = _job(owner_user_id=actor.id, status=SeatingExportJobStatus.PROCESSING)
    jobs.get_latest_in_flight_for_draft.return_value = in_flight_job
    jobs.get_latest_downloadable_for_draft.return_value = _job(
        owner_user_id=actor.id,
        status=SeatingExportJobStatus.SUCCEEDED,
        vault_file_id=uuid4(),
    )
    client.get_job.return_value = SimpleNamespace(job_id="upstream-1", status="running")

    handler = GetRecoverableSeatingExportJobForDraftHandler(
        jobs=jobs,
        vault_files=vault_files,
        client=client,
        finalizer=finalizer,
        uow=_DummyUow(),
    )

    result = await handler.handle(
        actor=actor,
        draft_id=in_flight_job.draft_id,
        correlation_id="corr-1",
    )

    assert result is not None
    assert result.job_id == in_flight_job.id
    assert result.status is SeatingExportJobStatus.PROCESSING
    jobs.get_latest_downloadable_for_draft.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_recoverable_seating_export_job_for_draft_falls_back_to_latest_downloadable() -> (
    None
):
    actor = make_user()
    downloadable_file_id = uuid4()
    jobs = AsyncMock(spec=SeatingExportJobRepositoryProtocol)
    vault_files = AsyncMock(spec=VaultFileRepositoryProtocol)
    client = AsyncMock(spec=SirConvertALotClientV2Protocol)
    finalizer = AsyncMock(spec=SeatingExportJobFinalizer)
    failed_in_flight_job = _job(owner_user_id=actor.id, status=SeatingExportJobStatus.PROCESSING)
    downloadable_job = _job(
        owner_user_id=actor.id,
        status=SeatingExportJobStatus.SUCCEEDED,
        vault_file_id=downloadable_file_id,
        upstream_job_id="upstream-2",
    )
    jobs.get_latest_in_flight_for_draft.return_value = failed_in_flight_job
    jobs.get_latest_downloadable_for_draft.return_value = downloadable_job
    client.get_job.return_value = SimpleNamespace(job_id="upstream-1", status="failed")
    finalizer.mark_failed.return_value = failed_in_flight_job.model_copy(
        update={
            "status": SeatingExportJobStatus.FAILED,
            "error_message": "PDF-exporten kunde inte slutföras.",
        }
    )
    vault_files.get_by_id.return_value = VaultFile(
        id=downloadable_file_id,
        user_id=actor.id,
        name="klass-7a-a3.pdf",
        bytes=12345,
        source_kind=VaultFileSourceKind.APP_EXPORT,
        source_run_id=None,
        source_artifact_id="classroom.group-seating-studio",
        created_at=datetime(2026, 3, 24, tzinfo=timezone.utc),
        deleted_at=None,
    )

    handler = GetRecoverableSeatingExportJobForDraftHandler(
        jobs=jobs,
        vault_files=vault_files,
        client=client,
        finalizer=finalizer,
        uow=_DummyUow(),
    )

    result = await handler.handle(
        actor=actor,
        draft_id=failed_in_flight_job.draft_id,
        correlation_id="corr-1",
    )

    assert result is not None
    assert result.job_id == downloadable_job.id
    assert result.status is SeatingExportJobStatus.SUCCEEDED
    assert result.vault_artifact is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_recoverable_seating_export_job_for_draft_returns_none_when_no_job_exists() -> (
    None
):
    actor = make_user()
    jobs = AsyncMock(spec=SeatingExportJobRepositoryProtocol)
    vault_files = AsyncMock(spec=VaultFileRepositoryProtocol)
    client = AsyncMock(spec=SirConvertALotClientV2Protocol)
    finalizer = AsyncMock(spec=SeatingExportJobFinalizer)
    jobs.get_latest_in_flight_for_draft.return_value = None
    jobs.get_latest_downloadable_for_draft.return_value = None

    handler = GetRecoverableSeatingExportJobForDraftHandler(
        jobs=jobs,
        vault_files=vault_files,
        client=client,
        finalizer=finalizer,
        uow=_DummyUow(),
    )

    result = await handler.handle(actor=actor, draft_id=uuid4(), correlation_id="corr-1")

    assert result is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_recoverable_seating_export_job_for_draft_falls_back_when_refresh_raises() -> (
    None
):
    actor = make_user()
    downloadable_file_id = uuid4()
    jobs = AsyncMock(spec=SeatingExportJobRepositoryProtocol)
    vault_files = AsyncMock(spec=VaultFileRepositoryProtocol)
    client = AsyncMock(spec=SirConvertALotClientV2Protocol)
    finalizer = AsyncMock(spec=SeatingExportJobFinalizer)
    in_flight_job = _job(owner_user_id=actor.id, status=SeatingExportJobStatus.PROCESSING)
    downloadable_job = _job(
        owner_user_id=actor.id,
        status=SeatingExportJobStatus.SUCCEEDED,
        vault_file_id=downloadable_file_id,
        upstream_job_id="upstream-2",
    )
    jobs.get_latest_in_flight_for_draft.return_value = in_flight_job
    jobs.get_latest_downloadable_for_draft.return_value = downloadable_job
    client.get_job.side_effect = RuntimeError("sir-convert unavailable")
    vault_files.get_by_id.return_value = VaultFile(
        id=downloadable_file_id,
        user_id=actor.id,
        name="klass-7a-a3.pdf",
        bytes=12345,
        source_kind=VaultFileSourceKind.APP_EXPORT,
        source_run_id=None,
        source_artifact_id="classroom.group-seating-studio",
        created_at=datetime(2026, 3, 24, tzinfo=timezone.utc),
        deleted_at=None,
    )

    handler = GetRecoverableSeatingExportJobForDraftHandler(
        jobs=jobs,
        vault_files=vault_files,
        client=client,
        finalizer=finalizer,
        uow=_DummyUow(),
    )

    result = await handler.handle(
        actor=actor,
        draft_id=in_flight_job.draft_id,
        correlation_id="corr-1",
    )

    assert result is not None
    assert result.job_id == downloadable_job.id
    assert result.status is SeatingExportJobStatus.SUCCEEDED
    finalizer.mark_failed.assert_not_awaited()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_webhook_completion_saves_pdf_to_vault_and_marks_job_succeeded():
    actor = make_user()
    now = datetime(2026, 3, 24, tzinfo=timezone.utc)
    file_id = uuid4()
    jobs = AsyncMock(spec=SeatingExportJobRepositoryProtocol)
    client = AsyncMock(spec=SirConvertALotClientV2Protocol)
    vault_files = AsyncMock(spec=VaultFileRepositoryProtocol)
    vault_usage = AsyncMock(spec=VaultUsageRepositoryProtocol)
    vault_storage = AsyncMock(spec=VaultStorageProtocol)
    job = _job(owner_user_id=actor.id, status=SeatingExportJobStatus.PROCESSING)
    jobs.get_by_upstream_job_id.return_value = job
    client.download_artifact.return_value = SimpleNamespace(
        artifact=SimpleNamespace(filename="klassrumskarta.pdf", content=b"%PDF-1.4"),
    )
    vault_usage.get_for_update.return_value = SimpleNamespace(bytes_total=0)
    created_vault_file = VaultFile(
        id=file_id,
        user_id=actor.id,
        name="klass-7a-a3.pdf",
        bytes=8,
        source_kind=VaultFileSourceKind.APP_EXPORT,
        source_run_id=None,
        source_artifact_id="classroom.group-seating-studio",
        created_at=now,
        deleted_at=None,
    )
    vault_files.create.return_value = created_vault_file

    timestamp = "1710000000"
    body = b'{"job_id":"upstream-1","event_type":"job.succeeded"}'
    assert job.webhook_secret is not None
    signature = hmac.new(
        job.webhook_secret.encode("utf-8"),
        f"{timestamp}.".encode("utf-8") + body,
        hashlib.sha256,
    ).hexdigest()

    handler = CompleteSeatingExportJobFromWebhookHandler(
        jobs=jobs,
        finalizer=SeatingExportJobFinalizer(
            jobs=jobs,
            client=client,
            vault_files=vault_files,
            vault_usage=vault_usage,
            vault_storage=vault_storage,
            uow=_DummyUow(),
            clock=_FixedClock(now),
            id_generator=_FixedIdGenerator([file_id]),
            settings=Settings(VAULT_MAX_FILE_BYTES=1000, VAULT_MAX_TOTAL_BYTES=10_000),
        ),
        uow=_DummyUow(),
    )

    await handler.handle(
        headers={
            "x-scal-webhook-timestamp": timestamp,
            "x-scal-webhook-signature": f"v1={signature}",
        },
        raw_body=body,
        correlation_id="corr-1",
    )

    vault_storage.store_file.assert_awaited_once()
    jobs.update.assert_awaited()
    created_file = vault_files.create.await_args.kwargs["file"]
    assert created_file.name == "klass-7a-a3.pdf"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_download_seating_export_job_reads_pdf_from_vault():
    actor = make_user()
    file_id = uuid4()
    jobs = AsyncMock(spec=SeatingExportJobRepositoryProtocol)
    vault_files = AsyncMock(spec=VaultFileRepositoryProtocol)
    vault_storage = AsyncMock(spec=VaultStorageProtocol)
    job = _job(
        owner_user_id=actor.id,
        status=SeatingExportJobStatus.SUCCEEDED,
        vault_file_id=file_id,
    )
    jobs.get_by_id.return_value = job
    vault_files.get_by_id.return_value = VaultFile(
        id=file_id,
        user_id=actor.id,
        name="klass-7a-a3.pdf",
        bytes=12,
        source_kind=VaultFileSourceKind.APP_EXPORT,
        source_run_id=None,
        source_artifact_id="classroom.group-seating-studio",
        created_at=datetime(2026, 3, 24, tzinfo=timezone.utc),
        deleted_at=None,
    )
    vault_storage.read_file.return_value = b"%PDF"

    handler = DownloadSeatingExportJobHandler(
        jobs=jobs,
        vault_files=vault_files,
        vault_storage=vault_storage,
        uow=_DummyUow(),
    )

    filename, content = await handler.handle(actor=actor, job_id=job.id)

    assert filename == "klass-7a-a3.pdf"
    assert content == b"%PDF"
