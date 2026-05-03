"""CLI command for Klassrumskartan share-preview thumbnail backfill.

Purpose:
    Generate missing or stale renderer-derived 1200x630 preview PNG rows for
    active legacy Klassrumskartan share links.

Relationships:
    - Uses the same application backfill handler and Playwright renderer as web
      share creation.
    - Persists through the share-artifact repository and Unit of Work.
"""

from __future__ import annotations

import asyncio

import typer

from skriptoteket.application.curated_apps.classroom_planner import (
    BackfillClassroomPlannerSharePreviewsHandler,
    CreateClassroomPlannerShareArtifactHandler,
)
from skriptoteket.cli._db import open_session
from skriptoteket.config import Settings
from skriptoteket.infrastructure.clock import UTCClock
from skriptoteket.infrastructure.curated_apps.apps.classroom_planner.share_preview_renderer import (
    ClassroomPlannerSharePreviewRendererSettings,
    PlaywrightClassroomPlannerSharePreviewRenderer,
)
from skriptoteket.infrastructure.curated_apps.apps.classroom_planner.share_renderer import (
    SEATING_SHARE_RENDERER_VERSION,
    StaticClassroomPlannerShareRenderer,
)
from skriptoteket.infrastructure.db.uow import SQLAlchemyUnitOfWork
from skriptoteket.infrastructure.id_generator import UUID4Generator
from skriptoteket.infrastructure.repositories.classroom_planner_share_artifacts import (
    PostgreSQLClassroomPlannerShareArtifactRepository,
)
from skriptoteket.infrastructure.token_generator import SecureTokenGenerator


def backfill_classroom_share_previews(
    limit: int | None = typer.Option(
        default=None,
        min=1,
        help="Maximum number of stale/missing preview rows to process.",
    ),
    fail_fast: bool = typer.Option(
        default=False,
        help="Stop on the first preview generation failure.",
    ),
) -> None:
    """Backfill active Klassrumskartan share-link preview thumbnails."""

    asyncio.run(_backfill_async(limit=limit, fail_fast=fail_fast))


async def _backfill_async(*, limit: int | None, fail_fast: bool) -> None:
    settings = Settings()
    clock = UTCClock()
    preview_renderer = PlaywrightClassroomPlannerSharePreviewRenderer(
        settings=ClassroomPlannerSharePreviewRendererSettings(
            timeout_seconds=settings.CLASSROOM_SHARE_PREVIEW_TIMEOUT_SECONDS,
            max_concurrency=settings.CLASSROOM_SHARE_PREVIEW_MAX_CONCURRENCY,
        )
    )
    async with open_session(settings) as session:
        shares = PostgreSQLClassroomPlannerShareArtifactRepository(session)
        uow = SQLAlchemyUnitOfWork(session)
        create_artifact = CreateClassroomPlannerShareArtifactHandler(
            shares=shares,
            uow=uow,
            clock=clock,
            id_generator=UUID4Generator(),
            token_generator=SecureTokenGenerator(),
            preview_renderer=preview_renderer,
        )
        handler = BackfillClassroomPlannerSharePreviewsHandler(
            shares=shares,
            uow=uow,
            clock=clock,
            create_artifact=create_artifact,
            renderer=StaticClassroomPlannerShareRenderer(),
            current_seating_renderer_version=SEATING_SHARE_RENDERER_VERSION,
        )
        result = await handler.handle(limit=limit, fail_fast=fail_fast)

    failed = ",".join(str(share_id) for share_id in result.failed_share_ids)
    typer.echo(
        "Backfill classroom share previews complete: "
        f"scanned={result.scanned} generated={result.generated} "
        f"refreshed={result.refreshed} "
        f"failed={len(result.failed_share_ids)} failed_share_ids={failed}"
    )
