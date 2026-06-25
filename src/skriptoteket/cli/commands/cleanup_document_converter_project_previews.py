"""Document Converter project preview cleanup command.

Purpose:
    Provide a cron-friendly operations entrypoint that enforces the 24-hour
    temporary retention contract for HTML/CSS project preview artifacts.

Relationships:
    Wires the application cleanup handler to the filesystem preview store and
    UTC clock without exposing any route-visible Document Converter UI.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer

from skriptoteket.application.curated_apps.handlers.document_converter_project_previews import (
    CleanupDocumentConverterProjectPreviewsHandler,
)
from skriptoteket.config import Settings
from skriptoteket.infrastructure.clock import UTCClock
from skriptoteket.infrastructure.documents.document_converter_project_previews import (
    FilesystemDocumentConverterProjectPreviewStore,
)


def cleanup_document_converter_project_previews(
    artifacts_root: Path | None = typer.Option(None, help="Override ARTIFACTS_ROOT"),
) -> None:
    """Delete expired Document Converter project previews (cron-friendly)."""
    asyncio.run(_cleanup_document_converter_project_previews_async(artifacts_root=artifacts_root))


async def _cleanup_document_converter_project_previews_async(
    *,
    artifacts_root: Path | None,
) -> None:
    settings = Settings()
    effective_root = settings.ARTIFACTS_ROOT if artifacts_root is None else artifacts_root
    clock = UTCClock()
    previews = FilesystemDocumentConverterProjectPreviewStore(artifacts_root=effective_root)
    handler = CleanupDocumentConverterProjectPreviewsHandler(previews=previews, clock=clock)

    result = await handler.handle()
    typer.echo(
        "Cleanup Document Converter project previews complete: "
        f"deleted_previews={result.deleted_previews} "
        f"deleted_artifacts={result.deleted_artifacts} "
        f"artifacts_root={effective_root}"
    )
