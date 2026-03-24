"""Focused behavior tests for shared seating-export webhook dispatch."""

from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.classroom_planner import (
    CompleteSeatingExportJobFromWebhookHandler,
    CreateSeatingExportJobHandler,
    PrepareSeatingExportHandler,
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
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.protocols.classroom_planner_exports import (
    SeatingExportJobRepositoryProtocol,
    SeatingExportWebhookBindingRepositoryProtocol,
    SeatingPosterRendererProtocol,
)
from skriptoteket.protocols.sir_convert_a_lot_v2 import (
    SirConvertALotClientV2Protocol,
    SirConvertSubmittedJobV2,
    SirConvertWebhookSubscriptionSummaryV2,
    SirConvertWebhookSubscriptionV2,
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


def _job(*, owner_user_id, status: SeatingExportJobStatus) -> SeatingExportJob:
    prepared = _prepared_contract()
    now = datetime(2026, 3, 24, tzinfo=timezone.utc)
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
        upstream_job_id="upstream-1",
        webhook_subscription_id="whsub-shared",
        webhook_secret="whsec-shared",
        created_at=now,
        updated_at=now,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_seating_export_job_reuses_existing_shared_webhook_binding():
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
    client.list_webhook_subscriptions.return_value = [
        SirConvertWebhookSubscriptionSummaryV2(
            subscription_id="whsub-shared",
            callback_url="http://127.0.0.1:8000/api/v1/internal/sir-convert-a-lot/classroom-planner/seating-export-jobs",
        )
    ]
    client.submit_job.return_value = SirConvertSubmittedJobV2(
        job_id="upstream-2",
        status="queued",
        idempotent_replay=False,
    )
    created_job = _job(owner_user_id=actor.id, status=SeatingExportJobStatus.SUBMITTED).model_copy(
        update={
            "id": uuid4(),
            "upstream_job_id": None,
            "webhook_subscription_id": None,
            "webhook_secret": None,
        }
    )
    bound_job = created_job.model_copy(
        update={
            "webhook_subscription_id": "whsub-shared",
            "webhook_secret": "whsec-shared",
        }
    )
    submitted_job = bound_job.model_copy(update={"upstream_job_id": "upstream-2"})
    jobs.create.return_value = created_job
    jobs.update.side_effect = [bound_job, submitted_job]
    bindings.get_shared_for_update.return_value = _DummyBinding(
        subscription_id="whsub-shared",
        callback_url="http://127.0.0.1:8000/api/v1/internal/sir-convert-a-lot/classroom-planner/seating-export-jobs",
        secret="whsec-shared",
    )

    handler = CreateSeatingExportJobHandler(
        prepare=prepare,
        jobs=jobs,
        webhook_bindings=bindings,
        renderer=renderer,
        client=client,
        uow=_DummyUow(),
        clock=_FixedClock(now),
        id_generator=_FixedIdGenerator([created_job.id]),
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

    assert result.status is SeatingExportJobStatus.SUBMITTED
    client.create_webhook_subscription.assert_not_called()
    first_update = jobs.update.await_args_list[0].kwargs["job"]
    assert first_update.webhook_subscription_id == "whsub-shared"
    assert first_update.webhook_secret == "whsec-shared"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_seating_export_job_recreates_missing_shared_webhook_binding():
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
    client.list_webhook_subscriptions.return_value = []
    client.create_webhook_subscription.return_value = SirConvertWebhookSubscriptionV2(
        subscription_id="whsub-new",
        callback_url="http://127.0.0.1:8000/api/v1/internal/sir-convert-a-lot/classroom-planner/seating-export-jobs",
        secret="whsec-new",
    )
    client.submit_job.return_value = SirConvertSubmittedJobV2(
        job_id="upstream-2",
        status="queued",
        idempotent_replay=False,
    )
    created_job = _job(owner_user_id=actor.id, status=SeatingExportJobStatus.SUBMITTED).model_copy(
        update={
            "id": uuid4(),
            "upstream_job_id": None,
            "webhook_subscription_id": None,
            "webhook_secret": None,
        }
    )
    rebound_job = created_job.model_copy(
        update={
            "webhook_subscription_id": "whsub-new",
            "webhook_secret": "whsec-new",
        }
    )
    submitted_job = rebound_job.model_copy(update={"upstream_job_id": "upstream-2"})
    jobs.create.return_value = created_job
    jobs.update.side_effect = [rebound_job, submitted_job]
    bindings.get_shared_for_update.return_value = _DummyBinding(
        subscription_id="whsub-stale",
        callback_url="http://127.0.0.1:8000/api/v1/internal/sir-convert-a-lot/classroom-planner/seating-export-jobs",
        secret="whsec-stale",
    )
    bindings.update_shared.return_value = _DummyBinding(
        subscription_id="whsub-new",
        callback_url="http://127.0.0.1:8000/api/v1/internal/sir-convert-a-lot/classroom-planner/seating-export-jobs",
        secret="whsec-new",
    )

    handler = CreateSeatingExportJobHandler(
        prepare=prepare,
        jobs=jobs,
        webhook_bindings=bindings,
        renderer=renderer,
        client=client,
        uow=_DummyUow(),
        clock=_FixedClock(now),
        id_generator=_FixedIdGenerator([created_job.id]),
        settings=Settings(SIR_CONVERT_A_LOT_V2_CALLBACK_BASE_URL="http://127.0.0.1:8000"),
    )

    await handler.handle(
        actor=actor,
        draft_id=created_job.draft_id,
        export_kind=SeatingExportKind.PDF,
        layout_id=SeatingExportLayoutId.PRETTY_BRUTALIST_POSTER,
        paper_size=SeatingExportPaperSize.A3_LANDSCAPE,
        correlation_id="corr-1",
    )

    client.create_webhook_subscription.assert_awaited_once()
    first_update = jobs.update.await_args_list[0].kwargs["job"]
    assert first_update.webhook_subscription_id == "whsub-new"
    assert first_update.webhook_secret == "whsec-new"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_seating_export_job_fails_closed_when_canonical_binding_secret_is_missing():
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
    client.list_webhook_subscriptions.return_value = [
        SirConvertWebhookSubscriptionSummaryV2(
            subscription_id="whsub-shared",
            callback_url="http://127.0.0.1:8000/api/v1/internal/sir-convert-a-lot/classroom-planner/seating-export-jobs",
        )
    ]
    created_job = _job(owner_user_id=actor.id, status=SeatingExportJobStatus.SUBMITTED).model_copy(
        update={
            "id": uuid4(),
            "upstream_job_id": None,
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
    bindings.get_shared_for_update.return_value = _DummyBinding(
        subscription_id="whsub-shared",
        callback_url="http://127.0.0.1:8000/api/v1/internal/sir-convert-a-lot/classroom-planner/seating-export-jobs",
        secret=None,
    )

    handler = CreateSeatingExportJobHandler(
        prepare=prepare,
        jobs=jobs,
        webhook_bindings=bindings,
        renderer=renderer,
        client=client,
        uow=_DummyUow(),
        clock=_FixedClock(now),
        id_generator=_FixedIdGenerator([created_job.id]),
        settings=Settings(SIR_CONVERT_A_LOT_V2_CALLBACK_BASE_URL="http://127.0.0.1:8000"),
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            draft_id=created_job.draft_id,
            export_kind=SeatingExportKind.PDF,
            layout_id=SeatingExportLayoutId.PRETTY_BRUTALIST_POSTER,
            paper_size=SeatingExportPaperSize.A3_LANDSCAPE,
            correlation_id="corr-1",
        )

    assert exc_info.value.code == ErrorCode.SERVICE_UNAVAILABLE
    client.create_webhook_subscription.assert_not_called()
    client.submit_job.assert_not_called()
    bindings.update_shared.assert_not_called()
    failed_update = jobs.update.await_args.kwargs["job"]
    assert failed_update.status is SeatingExportJobStatus.FAILED
    assert failed_update.error_message == "Kunde inte starta PDF-exporten just nu. Försök igen."


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_seating_export_job_recreates_shared_binding_when_callback_url_is_stale():
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
    client.list_webhook_subscriptions.return_value = [
        SirConvertWebhookSubscriptionSummaryV2(
            subscription_id="whsub-old",
            callback_url="http://127.0.0.1:8000/api/v1/internal/sir-convert-a-lot/classroom-planner/seating-export-jobs",
        )
    ]
    client.create_webhook_subscription.return_value = SirConvertWebhookSubscriptionV2(
        subscription_id="whsub-new",
        callback_url="http://127.0.0.1:8001/api/v1/internal/sir-convert-a-lot/classroom-planner/seating-export-jobs",
        secret="whsec-new",
    )
    client.submit_job.return_value = SirConvertSubmittedJobV2(
        job_id="upstream-2",
        status="queued",
        idempotent_replay=False,
    )
    created_job = _job(owner_user_id=actor.id, status=SeatingExportJobStatus.SUBMITTED).model_copy(
        update={
            "id": uuid4(),
            "upstream_job_id": None,
            "webhook_subscription_id": None,
            "webhook_secret": None,
        }
    )
    rebound_job = created_job.model_copy(
        update={
            "webhook_subscription_id": "whsub-new",
            "webhook_secret": "whsec-new",
        }
    )
    submitted_job = rebound_job.model_copy(update={"upstream_job_id": "upstream-2"})
    jobs.create.return_value = created_job
    jobs.update.side_effect = [rebound_job, submitted_job]
    bindings.get_shared_for_update.return_value = _DummyBinding(
        subscription_id="whsub-old",
        callback_url="http://127.0.0.1:8000/api/v1/internal/sir-convert-a-lot/classroom-planner/seating-export-jobs",
        secret="whsec-old",
    )
    bindings.update_shared.return_value = _DummyBinding(
        subscription_id="whsub-new",
        callback_url="http://127.0.0.1:8001/api/v1/internal/sir-convert-a-lot/classroom-planner/seating-export-jobs",
        secret="whsec-new",
    )

    handler = CreateSeatingExportJobHandler(
        prepare=prepare,
        jobs=jobs,
        webhook_bindings=bindings,
        renderer=renderer,
        client=client,
        uow=_DummyUow(),
        clock=_FixedClock(now),
        id_generator=_FixedIdGenerator([created_job.id]),
        settings=Settings(SIR_CONVERT_A_LOT_V2_CALLBACK_BASE_URL="http://127.0.0.1:8001"),
    )

    await handler.handle(
        actor=actor,
        draft_id=created_job.draft_id,
        export_kind=SeatingExportKind.PDF,
        layout_id=SeatingExportLayoutId.PRETTY_BRUTALIST_POSTER,
        paper_size=SeatingExportPaperSize.A3_LANDSCAPE,
        correlation_id="corr-1",
    )

    client.create_webhook_subscription.assert_awaited_once()
    bindings.update_shared.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_webhook_completion_dispatches_by_upstream_job_id():
    actor = make_user()
    jobs = AsyncMock(spec=SeatingExportJobRepositoryProtocol)
    finalizer = AsyncMock()
    job = _job(owner_user_id=actor.id, status=SeatingExportJobStatus.PROCESSING)
    jobs.get_by_upstream_job_id.return_value = job

    timestamp = "1710000000"
    raw_body = b'{"job_id":"upstream-1","event_type":"job.succeeded"}'
    assert job.webhook_secret is not None
    signature = hmac.new(
        job.webhook_secret.encode("utf-8"),
        f"{timestamp}.".encode("utf-8") + raw_body,
        hashlib.sha256,
    ).hexdigest()

    handler = CompleteSeatingExportJobFromWebhookHandler(
        jobs=jobs,
        finalizer=finalizer,
        uow=_DummyUow(),
    )

    await handler.handle(
        headers={
            "x-scal-webhook-timestamp": timestamp,
            "x-scal-webhook-signature": f"v1={signature}",
        },
        raw_body=raw_body,
        correlation_id="corr-1",
    )

    jobs.get_by_upstream_job_id.assert_awaited_once_with(upstream_job_id="upstream-1")
    finalizer.complete_success.assert_awaited_once_with(job=job, correlation_id="corr-1")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_webhook_completion_ignores_unknown_upstream_job():
    jobs = AsyncMock(spec=SeatingExportJobRepositoryProtocol)
    jobs.get_by_upstream_job_id.return_value = None
    finalizer = AsyncMock()
    handler = CompleteSeatingExportJobFromWebhookHandler(
        jobs=jobs,
        finalizer=finalizer,
        uow=_DummyUow(),
    )

    await handler.handle(
        headers={},
        raw_body=b'{"job_id":"missing","event_type":"job.succeeded"}',
        correlation_id="corr-1",
    )

    finalizer.complete_success.assert_not_called()
