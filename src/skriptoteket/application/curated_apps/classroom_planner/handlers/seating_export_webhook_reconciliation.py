"""Reconcile seating-export webhook state against Sir Convert subscriptions.

Purpose:
    Provide one deterministic application-layer repair step for production
    seating-export readiness by classifying upstream Sir Convert webhook
    subscriptions, deleting invalid callback state, and ensuring exactly one
    canonical shared binding with a known secret remains in Skriptoteket.

Relationships:
    - Uses `SeatingExportWebhookBindingRepositoryProtocol` for the local shared
      binding record and `SirConvertALotClientV2Protocol` for upstream webhook
      inventory/mutation.
    - Shares callback-path rules with seating export-job creation through
      `exports.webhook_contract`.
    - Invoked by the PR-0122 production CLI/operator flow.
"""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlparse

from skriptoteket.application.curated_apps.classroom_planner.exports.webhook_contract import (
    SEATING_EXPORT_SHARED_WEBHOOK_PATH,
    SEATING_EXPORT_WEBHOOK_EVENT_TYPES,
    build_seating_export_callback_url,
    is_seating_export_shared_callback_url,
)
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode, validation_error
from skriptoteket.protocols.classroom_planner_exports import (
    SeatingExportWebhookBindingRepositoryProtocol,
)
from skriptoteket.protocols.sir_convert_a_lot_v2 import (
    SirConvertALotClientV2Protocol,
    SirConvertWebhookSubscriptionSummaryV2,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol


@dataclass(frozen=True, slots=True)
class SeatingExportWebhookReconciliationResult:
    """Summarize one seating-export webhook reconciliation attempt."""

    expected_callback_url: str
    active_subscription_id: str
    created_subscription_id: str | None
    listed_subscription_ids: tuple[str, ...]
    deleted_subscription_ids: tuple[str, ...]
    deleted_duplicate_canonical_subscription_ids: tuple[str, ...]
    deleted_legacy_subscription_ids: tuple[str, ...]
    deleted_stale_subscription_ids: tuple[str, ...]


class ReconcileSeatingExportWebhooksHandler:
    """Repair or verify the canonical seating-export shared webhook binding."""

    def __init__(
        self,
        *,
        webhook_bindings: SeatingExportWebhookBindingRepositoryProtocol,
        client: SirConvertALotClientV2Protocol,
        uow: UnitOfWorkProtocol,
        settings: Settings,
    ) -> None:
        self._webhook_bindings = webhook_bindings
        self._client = client
        self._uow = uow
        self._settings = settings

    async def handle(
        self,
        *,
        correlation_id: str | None,
    ) -> SeatingExportWebhookReconciliationResult:
        callback_base_url = self._settings.SIR_CONVERT_A_LOT_V2_CALLBACK_BASE_URL.strip()
        if callback_base_url == "":
            raise validation_error("PDF-export är inte konfigurerad ännu.")
        expected_callback_url = build_seating_export_callback_url(
            callback_base_url=callback_base_url
        )

        async with self._uow:
            binding = await self._webhook_bindings.get_shared_for_update()
            subscriptions = await self._client.list_webhook_subscriptions(
                correlation_id=correlation_id
            )

            canonical_subscriptions = tuple(
                subscription
                for subscription in subscriptions
                if subscription.callback_url == expected_callback_url
            )
            stale_shared_subscriptions = tuple(
                subscription
                for subscription in subscriptions
                if is_seating_export_shared_callback_url(callback_url=subscription.callback_url)
                and subscription.callback_url != expected_callback_url
            )
            legacy_subscriptions = tuple(
                subscription
                for subscription in subscriptions
                if self._is_legacy_callback_url(callback_url=subscription.callback_url)
            )
            listed_subscription_ids = tuple(
                subscription.subscription_id for subscription in subscriptions
            )

            if self._can_keep_existing_binding(
                binding_subscription_id=binding.subscription_id,
                binding_callback_url=binding.callback_url,
                binding_secret=binding.secret,
                expected_callback_url=expected_callback_url,
                canonical_subscriptions=canonical_subscriptions,
            ):
                duplicate_canonical_subscriptions = tuple(
                    subscription
                    for subscription in canonical_subscriptions
                    if subscription.subscription_id != binding.subscription_id
                )
                deleted_subscription_ids = await self._delete_subscriptions(
                    subscriptions=self._dedupe_subscriptions(
                        duplicate_canonical_subscriptions
                        + stale_shared_subscriptions
                        + legacy_subscriptions
                    ),
                    correlation_id=correlation_id,
                )
                if binding.subscription_id is None:
                    raise DomainError(
                        code=ErrorCode.SERVICE_UNAVAILABLE,
                        message=(
                            "Shared seating-export webhook binding is missing a subscription id."
                        ),
                        details={},
                    )
                return SeatingExportWebhookReconciliationResult(
                    expected_callback_url=expected_callback_url,
                    active_subscription_id=binding.subscription_id,
                    created_subscription_id=None,
                    listed_subscription_ids=listed_subscription_ids,
                    deleted_subscription_ids=deleted_subscription_ids,
                    deleted_duplicate_canonical_subscription_ids=tuple(
                        subscription.subscription_id
                        for subscription in self._dedupe_subscriptions(
                            duplicate_canonical_subscriptions
                        )
                    ),
                    deleted_legacy_subscription_ids=tuple(
                        subscription.subscription_id
                        for subscription in self._dedupe_subscriptions(legacy_subscriptions)
                    ),
                    deleted_stale_subscription_ids=tuple(
                        subscription.subscription_id
                        for subscription in self._dedupe_subscriptions(stale_shared_subscriptions)
                    ),
                )

            deleted_before_create: tuple[str, ...] = ()
            replaced_canonical_subscriptions: tuple[
                SirConvertWebhookSubscriptionSummaryV2, ...
            ] = ()
            if len(canonical_subscriptions) > 0:
                replaced_canonical_subscriptions = self._dedupe_subscriptions(
                    canonical_subscriptions
                )
                deleted_before_create = await self._delete_subscriptions(
                    subscriptions=self._dedupe_subscriptions(
                        replaced_canonical_subscriptions
                        + stale_shared_subscriptions
                        + legacy_subscriptions
                    ),
                    correlation_id=correlation_id,
                )

            created_subscription = await self._client.create_webhook_subscription(
                callback_url=expected_callback_url,
                event_types=list(SEATING_EXPORT_WEBHOOK_EVENT_TYPES),
                correlation_id=correlation_id,
            )
            if created_subscription.callback_url != expected_callback_url:
                raise DomainError(
                    code=ErrorCode.SERVICE_UNAVAILABLE,
                    message=(
                        "Sir Convert-a-Lot returned a mismatched callback URL during "
                        "seating-export webhook reconciliation."
                    ),
                    details={
                        "expected_callback_url": expected_callback_url,
                        "actual_callback_url": created_subscription.callback_url,
                    },
                )
            try:
                updated_binding = await self._webhook_bindings.update_shared(
                    binding=binding.model_copy(
                        update={
                            "subscription_id": created_subscription.subscription_id,
                            "callback_url": created_subscription.callback_url,
                            "secret": created_subscription.secret,
                        }
                    )
                )
            except Exception:
                await self._client.delete_webhook_subscription(
                    created_subscription.subscription_id,
                    correlation_id=correlation_id,
                )
                raise
            if updated_binding.subscription_id is None:
                await self._client.delete_webhook_subscription(
                    created_subscription.subscription_id,
                    correlation_id=correlation_id,
                )
                raise DomainError(
                    code=ErrorCode.SERVICE_UNAVAILABLE,
                    message="Failed to persist the seating-export shared webhook binding.",
                    details={"expected_callback_url": expected_callback_url},
                )
            deleted_subscription_ids = deleted_before_create
            if len(replaced_canonical_subscriptions) == 0:
                deleted_subscription_ids = await self._delete_subscriptions(
                    subscriptions=self._dedupe_subscriptions(
                        stale_shared_subscriptions + legacy_subscriptions
                    ),
                    correlation_id=correlation_id,
                )
            duplicate_canonical_ids = tuple(
                subscription.subscription_id for subscription in replaced_canonical_subscriptions
            )
            legacy_ids = tuple(
                subscription.subscription_id
                for subscription in self._dedupe_subscriptions(legacy_subscriptions)
            )
            stale_ids = tuple(
                subscription.subscription_id
                for subscription in self._dedupe_subscriptions(stale_shared_subscriptions)
            )
            return SeatingExportWebhookReconciliationResult(
                expected_callback_url=expected_callback_url,
                active_subscription_id=updated_binding.subscription_id,
                created_subscription_id=created_subscription.subscription_id,
                listed_subscription_ids=listed_subscription_ids,
                deleted_subscription_ids=deleted_subscription_ids,
                deleted_duplicate_canonical_subscription_ids=duplicate_canonical_ids,
                deleted_legacy_subscription_ids=legacy_ids,
                deleted_stale_subscription_ids=stale_ids,
            )

    def _can_keep_existing_binding(
        self,
        *,
        binding_subscription_id: str | None,
        binding_callback_url: str | None,
        binding_secret: str | None,
        expected_callback_url: str,
        canonical_subscriptions: tuple[SirConvertWebhookSubscriptionSummaryV2, ...],
    ) -> bool:
        if (
            binding_subscription_id is None
            or binding_callback_url != expected_callback_url
            or binding_secret is None
        ):
            return False
        return any(
            subscription.subscription_id == binding_subscription_id
            for subscription in canonical_subscriptions
        )

    async def _delete_subscriptions(
        self,
        *,
        subscriptions: tuple[SirConvertWebhookSubscriptionSummaryV2, ...],
        correlation_id: str | None,
    ) -> tuple[str, ...]:
        deleted_ids: list[str] = []
        for subscription in subscriptions:
            await self._client.delete_webhook_subscription(
                subscription.subscription_id,
                correlation_id=correlation_id,
            )
            deleted_ids.append(subscription.subscription_id)
        return tuple(deleted_ids)

    def _dedupe_subscriptions(
        self,
        subscriptions: tuple[SirConvertWebhookSubscriptionSummaryV2, ...],
    ) -> tuple[SirConvertWebhookSubscriptionSummaryV2, ...]:
        seen: set[str] = set()
        deduped: list[SirConvertWebhookSubscriptionSummaryV2] = []
        for subscription in subscriptions:
            if subscription.subscription_id in seen:
                continue
            seen.add(subscription.subscription_id)
            deduped.append(subscription)
        return tuple(deduped)

    def _is_legacy_callback_url(self, *, callback_url: str) -> bool:
        """Return whether one callback URL targets the retired per-job route."""

        return urlparse(callback_url).path.startswith(f"{SEATING_EXPORT_SHARED_WEBHOOK_PATH}/")
