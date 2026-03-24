"""CLI entrypoint for seating-export webhook reconciliation.

Purpose:
    Expose the PR-0122 seating-export webhook repair step as a deterministic
    container-local command that production operators can invoke from the
    canonical Hemma wrapper after deploy.

Relationships:
    - Uses the application-layer reconciliation handler to inventory, delete,
      and recreate invalid Sir Convert webhook subscriptions until exactly one
      canonical shared callback remains.
    - Consumed by `scripts/hemma_deploy_and_verify_seating_export.sh`.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import asdict
from uuid import uuid4

import httpx
import typer

from skriptoteket.application.curated_apps.classroom_planner.handlers import (
    seating_export_webhook_reconciliation as seating_export_webhook_reconciliation_handler,
)
from skriptoteket.cli._db import open_session
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.sir_convert_client_v2 import (
    SirConvertALotClientV2,
    SirConvertClientSettingsV2,
)
from skriptoteket.infrastructure.db.uow import SQLAlchemyUnitOfWork
from skriptoteket.infrastructure.repositories.classroom_planner_export_webhook_bindings import (
    PostgreSQLSeatingExportWebhookBindingRepository,
)


def reconcile_seating_export_webhooks(
    correlation_id: str | None = typer.Option(
        None,
        help="Optional correlation id for upstream and local reconciliation calls.",
    ),
) -> None:
    """Repair or verify canonical-only seating-export webhook state."""

    asyncio.run(_reconcile_seating_export_webhooks_async(correlation_id=correlation_id))


async def _reconcile_seating_export_webhooks_async(*, correlation_id: str | None) -> None:
    settings = Settings()
    if settings.SIR_CONVERT_A_LOT_V2_BASE_URL.strip() == "":
        raise SystemExit("Missing SIR_CONVERT_A_LOT_V2_BASE_URL for webhook reconciliation.")
    if settings.SIR_CONVERT_A_LOT_V2_API_KEY.strip() == "":
        raise SystemExit("Missing SIR_CONVERT_A_LOT_V2_API_KEY for webhook reconciliation.")

    effective_correlation_id = correlation_id or f"seat-webhook-reconcile-{uuid4()}"
    client_settings = SirConvertClientSettingsV2(
        base_url=settings.SIR_CONVERT_A_LOT_V2_BASE_URL,
        api_key=settings.SIR_CONVERT_A_LOT_V2_API_KEY,
        timeout_seconds=settings.SIR_CONVERT_A_LOT_V2_TIMEOUT_SECONDS,
    )
    reconciler_cls = (
        seating_export_webhook_reconciliation_handler.ReconcileSeatingExportWebhooksHandler
    )

    try:
        async with open_session(settings) as session:
            async with httpx.AsyncClient(
                base_url=client_settings.base_url,
                timeout=client_settings.timeout_seconds,
            ) as http_client:
                handler = reconciler_cls(
                    webhook_bindings=PostgreSQLSeatingExportWebhookBindingRepository(session),
                    client=SirConvertALotClientV2(
                        settings=client_settings,
                        client=http_client,
                    ),
                    uow=SQLAlchemyUnitOfWork(session),
                    settings=settings,
                )
                result = await handler.handle(correlation_id=effective_correlation_id)
    except DomainError as exc:
        raise SystemExit(exc.message) from exc

    typer.echo(
        json.dumps(
            {
                **asdict(result),
                "correlation_id": effective_correlation_id,
            },
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )
    )
