"""Behavior tests for seating-export webhook reconciliation."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from skriptoteket.application.curated_apps.classroom_planner.handlers import (
    seating_export_webhook_reconciliation as seating_export_webhook_reconciliation_handler,
)
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.protocols.classroom_planner_exports import (
    SeatingExportWebhookBindingRepositoryProtocol,
)
from skriptoteket.protocols.sir_convert_a_lot_v2 import (
    SirConvertALotClientV2Protocol,
    SirConvertWebhookSubscriptionSummaryV2,
    SirConvertWebhookSubscriptionV2,
)


class _DummyUow:
    async def __aenter__(self) -> _DummyUow:
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


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


@pytest.mark.unit
@pytest.mark.asyncio
async def test_reconcile_keeps_valid_canonical_binding_and_deletes_legacy_subscriptions() -> None:
    bindings = AsyncMock(spec=SeatingExportWebhookBindingRepositoryProtocol)
    client = AsyncMock(spec=SirConvertALotClientV2Protocol)
    expected_callback_url = (
        "https://skriptoteket.hule.education"
        "/api/v1/internal/sir-convert-a-lot/classroom-planner/seating-export-jobs"
    )
    bindings.get_shared_for_update.return_value = _DummyBinding(
        subscription_id="whsub-canonical",
        callback_url=expected_callback_url,
        secret="whsec-canonical",
    )
    client.list_webhook_subscriptions.return_value = [
        SirConvertWebhookSubscriptionSummaryV2(
            subscription_id="whsub-canonical",
            callback_url=expected_callback_url,
        ),
        SirConvertWebhookSubscriptionSummaryV2(
            subscription_id="whsub-legacy",
            callback_url=(
                "https://skriptoteket.hule.education/api/v1/internal/"
                "sir-convert-a-lot/classroom-planner/seating-export-jobs/"
                "11111111-1111-1111-1111-111111111111"
            ),
        ),
    ]

    handler = seating_export_webhook_reconciliation_handler.ReconcileSeatingExportWebhooksHandler(
        webhook_bindings=bindings,
        client=client,
        uow=_DummyUow(),
        settings=Settings(
            SIR_CONVERT_A_LOT_V2_CALLBACK_BASE_URL="https://skriptoteket.hule.education"
        ),
    )

    result = await handler.handle(correlation_id="corr-1")

    assert result.active_subscription_id == "whsub-canonical"
    assert result.created_subscription_id is None
    assert result.listed_subscription_ids == ("whsub-canonical", "whsub-legacy")
    assert result.deleted_subscription_ids == ("whsub-legacy",)
    assert result.deleted_duplicate_canonical_subscription_ids == ()
    assert result.deleted_legacy_subscription_ids == ("whsub-legacy",)
    assert result.deleted_stale_subscription_ids == ()
    client.delete_webhook_subscription.assert_awaited_once_with(
        "whsub-legacy",
        correlation_id="corr-1",
    )
    client.create_webhook_subscription.assert_not_called()
    bindings.update_shared.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_reconcile_replaces_invalid_canonical_when_local_secret_missing() -> None:
    bindings = AsyncMock(spec=SeatingExportWebhookBindingRepositoryProtocol)
    client = AsyncMock(spec=SirConvertALotClientV2Protocol)
    expected_callback_url = (
        "https://skriptoteket.hule.education"
        "/api/v1/internal/sir-convert-a-lot/classroom-planner/seating-export-jobs"
    )
    bindings.get_shared_for_update.return_value = _DummyBinding(
        subscription_id="whsub-old",
        callback_url=expected_callback_url,
        secret=None,
    )
    bindings.update_shared.return_value = _DummyBinding(
        subscription_id="whsub-new",
        callback_url=expected_callback_url,
        secret="whsec-new",
    )
    client.list_webhook_subscriptions.return_value = [
        SirConvertWebhookSubscriptionSummaryV2(
            subscription_id="whsub-old",
            callback_url=expected_callback_url,
        )
    ]
    client.create_webhook_subscription.return_value = SirConvertWebhookSubscriptionV2(
        subscription_id="whsub-new",
        callback_url=expected_callback_url,
        secret="whsec-new",
    )

    handler = seating_export_webhook_reconciliation_handler.ReconcileSeatingExportWebhooksHandler(
        webhook_bindings=bindings,
        client=client,
        uow=_DummyUow(),
        settings=Settings(
            SIR_CONVERT_A_LOT_V2_CALLBACK_BASE_URL="https://skriptoteket.hule.education"
        ),
    )

    result = await handler.handle(correlation_id="corr-1")

    assert result.active_subscription_id == "whsub-new"
    assert result.created_subscription_id == "whsub-new"
    assert result.listed_subscription_ids == ("whsub-old",)
    assert result.deleted_subscription_ids == ("whsub-old",)
    assert result.deleted_duplicate_canonical_subscription_ids == ("whsub-old",)
    assert result.deleted_legacy_subscription_ids == ()
    assert result.deleted_stale_subscription_ids == ()
    client.delete_webhook_subscription.assert_awaited_once_with(
        "whsub-old",
        correlation_id="corr-1",
    )
    client.create_webhook_subscription.assert_awaited_once()
    bindings.update_shared.assert_awaited_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_reconcile_keeps_binding_and_deletes_duplicate_stale_and_legacy_subscriptions() -> (
    None
):
    bindings = AsyncMock(spec=SeatingExportWebhookBindingRepositoryProtocol)
    client = AsyncMock(spec=SirConvertALotClientV2Protocol)
    expected_callback_url = (
        "https://skriptoteket.hule.education"
        "/api/v1/internal/sir-convert-a-lot/classroom-planner/seating-export-jobs"
    )
    bindings.get_shared_for_update.return_value = _DummyBinding(
        subscription_id="whsub-keep",
        callback_url=expected_callback_url,
        secret="whsec-keep",
    )
    client.list_webhook_subscriptions.return_value = [
        SirConvertWebhookSubscriptionSummaryV2(
            subscription_id="whsub-keep",
            callback_url=expected_callback_url,
        ),
        SirConvertWebhookSubscriptionSummaryV2(
            subscription_id="whsub-duplicate",
            callback_url=expected_callback_url,
        ),
        SirConvertWebhookSubscriptionSummaryV2(
            subscription_id="whsub-stale-shared",
            callback_url=(
                "https://old-skriptoteket.hule.education/api/v1/internal/"
                "sir-convert-a-lot/classroom-planner/seating-export-jobs"
            ),
        ),
        SirConvertWebhookSubscriptionSummaryV2(
            subscription_id="whsub-legacy",
            callback_url=(
                "https://skriptoteket.hule.education/api/v1/internal/"
                "sir-convert-a-lot/classroom-planner/seating-export-jobs/"
                "22222222-2222-2222-2222-222222222222"
            ),
        ),
    ]
    handler = seating_export_webhook_reconciliation_handler.ReconcileSeatingExportWebhooksHandler(
        webhook_bindings=bindings,
        client=client,
        uow=_DummyUow(),
        settings=Settings(
            SIR_CONVERT_A_LOT_V2_CALLBACK_BASE_URL="https://skriptoteket.hule.education"
        ),
    )

    result = await handler.handle(correlation_id="corr-1")

    assert result.active_subscription_id == "whsub-keep"
    assert result.created_subscription_id is None
    assert result.listed_subscription_ids == (
        "whsub-keep",
        "whsub-duplicate",
        "whsub-stale-shared",
        "whsub-legacy",
    )
    assert result.deleted_subscription_ids == (
        "whsub-duplicate",
        "whsub-stale-shared",
        "whsub-legacy",
    )
    assert result.deleted_duplicate_canonical_subscription_ids == ("whsub-duplicate",)
    assert result.deleted_legacy_subscription_ids == ("whsub-legacy",)
    assert result.deleted_stale_subscription_ids == ("whsub-stale-shared",)
    client.create_webhook_subscription.assert_not_called()
    bindings.update_shared.assert_not_called()
    assert client.delete_webhook_subscription.await_count == 3


@pytest.mark.unit
@pytest.mark.asyncio
async def test_reconcile_create_failure_leaves_existing_subscriptions_intact() -> None:
    bindings = AsyncMock(spec=SeatingExportWebhookBindingRepositoryProtocol)
    client = AsyncMock(spec=SirConvertALotClientV2Protocol)
    expected_callback_url = (
        "https://skriptoteket.hule.education"
        "/api/v1/internal/sir-convert-a-lot/classroom-planner/seating-export-jobs"
    )
    bindings.get_shared_for_update.return_value = _DummyBinding(
        subscription_id="whsub-old",
        callback_url=expected_callback_url,
        secret=None,
    )
    client.list_webhook_subscriptions.return_value = []
    client.create_webhook_subscription.side_effect = RuntimeError("boom")

    handler = seating_export_webhook_reconciliation_handler.ReconcileSeatingExportWebhooksHandler(
        webhook_bindings=bindings,
        client=client,
        uow=_DummyUow(),
        settings=Settings(
            SIR_CONVERT_A_LOT_V2_CALLBACK_BASE_URL="https://skriptoteket.hule.education"
        ),
    )

    with pytest.raises(RuntimeError, match="boom"):
        await handler.handle(correlation_id="corr-1")

    client.delete_webhook_subscription.assert_not_called()
    bindings.update_shared.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_reconcile_requires_callback_base_url_configuration() -> None:
    bindings = AsyncMock(spec=SeatingExportWebhookBindingRepositoryProtocol)
    client = AsyncMock(spec=SirConvertALotClientV2Protocol)
    handler = seating_export_webhook_reconciliation_handler.ReconcileSeatingExportWebhooksHandler(
        webhook_bindings=bindings,
        client=client,
        uow=_DummyUow(),
        settings=Settings(SIR_CONVERT_A_LOT_V2_CALLBACK_BASE_URL=""),
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(correlation_id="corr-1")

    assert exc_info.value.code == ErrorCode.VALIDATION_ERROR
