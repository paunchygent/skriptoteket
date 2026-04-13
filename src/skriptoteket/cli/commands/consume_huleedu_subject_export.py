"""CLI command for consuming HuleEdu subject exports.

Purpose:
    Let operators apply sanitized HuleEdu subject exports to local
    Skriptoteket users, roles, and realm-aware identity projections.

Relationships:
    - Uses the application-layer `HuleEduSubjectExportConsumer`.
    - Writes only sanitized command summaries to optional artifact files.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Annotated

import typer

from skriptoteket.application.identity.huleedu_subject_export_consumer import (
    SUBJECT_EXPORT_CONSUME_RESULT_SCHEMA_VERSION,
    HuleEduSubjectExportConsumer,
    HuleEduSubjectExportResult,
)
from skriptoteket.application.identity.huleedu_subject_export_contract import (
    parse_huleedu_subject_export,
)
from skriptoteket.cli._db import open_session
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError
from skriptoteket.infrastructure.clock import UTCClock
from skriptoteket.infrastructure.db.uow import SQLAlchemyUnitOfWork
from skriptoteket.infrastructure.id_generator import UUID4Generator
from skriptoteket.infrastructure.repositories.identity_projection_repository import (
    PostgreSQLIdentityProjectionEventRepository,
    PostgreSQLIdentityProjectionRepository,
)
from skriptoteket.infrastructure.repositories.user_repository import PostgreSQLUserRepository


def consume_huleedu_subject_export(
    export_json: Annotated[
        Path,
        typer.Option(
            "--export-json",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            resolve_path=True,
            help="Sanitized HuleEdu subject export JSON.",
        ),
    ],
    output_json: Annotated[
        Path | None,
        typer.Option(
            "--output-json",
            file_okay=True,
            dir_okay=False,
            writable=True,
            resolve_path=True,
            help="Optional sanitized result artifact path.",
        ),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run/--apply",
            help="Preview database actions or apply them.",
        ),
    ] = True,
) -> None:
    """Consume a HuleEdu subject export into local projections."""
    try:
        payload = json.loads(export_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in export file: {export_json}") from exc

    try:
        result = asyncio.run(
            _consume_huleedu_subject_export_async(payload=payload, dry_run=dry_run)
        )
    except DomainError as exc:
        failure = _failure_payload(error=exc, dry_run=dry_run)
        if output_json is not None:
            _write_json(path=output_json, payload=failure)
        typer.echo(json.dumps(failure, ensure_ascii=False, indent=2), err=True)
        raise typer.Exit(code=1) from exc

    result_payload = result.model_dump(mode="json")
    if output_json is not None:
        _write_json(path=output_json, payload=result_payload)

    typer.echo(format_subject_export_result_summary(result))
    if output_json is not None:
        typer.echo(f"Wrote sanitized result: {output_json}")


async def _consume_huleedu_subject_export_async(
    *,
    payload: object,
    dry_run: bool,
) -> HuleEduSubjectExportResult:
    export = parse_huleedu_subject_export(payload)
    settings = Settings()
    async with open_session(settings) as session:
        consumer = HuleEduSubjectExportConsumer(
            uow=SQLAlchemyUnitOfWork(session),
            users=PostgreSQLUserRepository(session),
            projections=PostgreSQLIdentityProjectionRepository(session),
            projection_events=PostgreSQLIdentityProjectionEventRepository(session),
            clock=UTCClock(),
            id_generator=UUID4Generator(),
        )
        return await consumer.consume(export=export, dry_run=dry_run)


def _write_json(*, path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def format_subject_export_result_summary(result: HuleEduSubjectExportResult) -> str:
    """Return the operator-facing one-line summary for a consume result."""
    if result.dry_run:
        return (
            "HuleEdu subject export dry-run ok: "
            f"processed={result.processed}, "
            f"would_create_users={result.would_create_users}, "
            f"would_create_projections={result.would_create_projections}, "
            f"would_update_users={result.would_update_users}, "
            f"unchanged={result.unchanged}"
        )

    return (
        "HuleEdu subject export apply ok: "
        f"processed={result.processed}, "
        f"created_users={result.created_users}, "
        f"created_projections={result.created_projections}, "
        f"updated_users={result.updated_users}, "
        f"unchanged={result.unchanged}"
    )


def _failure_payload(*, error: DomainError, dry_run: bool) -> dict[str, object]:
    return {
        "schema_version": SUBJECT_EXPORT_CONSUME_RESULT_SCHEMA_VERSION,
        "status": "failed",
        "dry_run": dry_run,
        "error": {
            "code": error.code.value,
            "message": error.message,
            "details": error.details,
        },
    }
