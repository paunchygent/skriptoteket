"""CLI command for the repeatable Hemma staging proof fixture.

Purpose:
    Let `pdm run hemma-dev start|reset|fixture` ensure one harmless staging
    tool that the imported proof contributor maintains, with the contributor's
    draft. The command itself refuses every target except the Hemma staging
    database, so a direct invocation cannot write to production.

Relationships:
    - Reads the same sanitized HuleEdu subject export that
      `consume-huleedu-subject-export --apply` consumed.
    - Delegates to the application-layer `StagingProofFixture`.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Annotated

import typer
from sqlalchemy.engine import make_url

from skriptoteket.application.catalog.handlers.assign_maintainer import AssignMaintainerHandler
from skriptoteket.application.catalog.handlers.create_draft_tool import CreateDraftToolHandler
from skriptoteket.application.catalog.handlers.update_tool_slug import UpdateToolSlugHandler
from skriptoteket.application.catalog.staging_proof_fixture import (
    StagingProofFixture,
    StagingProofFixtureResult,
)
from skriptoteket.application.identity.huleedu_subject_export_contract import (
    parse_huleedu_subject_export,
)
from skriptoteket.application.scripting.handlers.create_draft_version import (
    CreateDraftVersionHandler,
)
from skriptoteket.cli._db import open_session
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.infrastructure.clock import UTCClock
from skriptoteket.infrastructure.db.uow import SQLAlchemyUnitOfWork
from skriptoteket.infrastructure.id_generator import UUID4Generator
from skriptoteket.infrastructure.repositories.draft_lock_repository import (
    PostgreSQLDraftLockRepository,
)
from skriptoteket.infrastructure.repositories.tool_maintainer_audit_repository import (
    PostgreSQLToolMaintainerAuditRepository,
)
from skriptoteket.infrastructure.repositories.tool_maintainer_repository import (
    PostgreSQLToolMaintainerRepository,
)
from skriptoteket.infrastructure.repositories.tool_repository import PostgreSQLToolRepository
from skriptoteket.infrastructure.repositories.tool_version_repository import (
    PostgreSQLToolVersionRepository,
)
from skriptoteket.infrastructure.repositories.user_repository import PostgreSQLUserRepository

STAGING_ENVIRONMENT = "staging"
STAGING_DATABASE_HOST = "db"
STAGING_DATABASE_NAME = "skriptoteket"


def setup_staging_proof_fixture(
    export_json: Annotated[
        Path,
        typer.Option(
            "--export-json",
            exists=True,
            file_okay=True,
            dir_okay=False,
            readable=True,
            resolve_path=True,
            help="Sanitized HuleEdu subject export JSON already consumed with --apply.",
        ),
    ],
) -> None:
    """Ensure the staging proof tool, its contributor maintainer, and the draft."""
    try:
        payload = json.loads(export_json.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"Invalid JSON in export file: {export_json}") from exc

    try:
        result = asyncio.run(_setup_async(payload=payload, settings=Settings()))
    except DomainError as exc:
        failure = {
            "status": "failed",
            "code": exc.code.value,
            "message": exc.message,
            "details": exc.details,
        }
        typer.echo(json.dumps(failure, ensure_ascii=False), err=True)
        raise typer.Exit(code=1) from exc

    typer.echo(format_staging_proof_fixture_summary(result))


def require_staging_target(settings: Settings) -> None:
    """Refuse any environment or database other than the Hemma staging database.

    Staging runs with `ENVIRONMENT=staging` against the `skriptoteket-dev`
    project's own `db` service; production uses `shared-postgres`.
    """
    database = make_url(settings.DATABASE_URL)
    if (
        settings.ENVIRONMENT != STAGING_ENVIRONMENT
        or database.host != STAGING_DATABASE_HOST
        or database.database != STAGING_DATABASE_NAME
    ):
        raise DomainError(
            code=ErrorCode.FORBIDDEN,
            message="The staging proof fixture runs only against the Hemma staging database",
            details={
                "environment": settings.ENVIRONMENT,
                "database_host": database.host,
                "database_name": database.database,
            },
        )


async def _setup_async(*, payload: object, settings: Settings) -> StagingProofFixtureResult:
    require_staging_target(settings)
    export = parse_huleedu_subject_export(payload)
    async with open_session(settings) as session:
        uow = SQLAlchemyUnitOfWork(session)
        users = PostgreSQLUserRepository(session)
        tools = PostgreSQLToolRepository(session)
        maintainers = PostgreSQLToolMaintainerRepository(session)
        versions = PostgreSQLToolVersionRepository(session)
        clock = UTCClock()
        id_generator = UUID4Generator()
        fixture = StagingProofFixture(
            uow=uow,
            users=users,
            tools=tools,
            maintainers=maintainers,
            versions=versions,
            create_draft_tool=CreateDraftToolHandler(
                uow=uow,
                tools=tools,
                maintainers=maintainers,
                clock=clock,
                id_generator=id_generator,
            ),
            update_tool_slug=UpdateToolSlugHandler(uow=uow, tools=tools, clock=clock),
            assign_maintainer=AssignMaintainerHandler(
                uow=uow,
                tools=tools,
                maintainers=maintainers,
                users=users,
                audit=PostgreSQLToolMaintainerAuditRepository(session),
                clock=clock,
                id_generator=id_generator,
            ),
            create_draft_version=CreateDraftVersionHandler(
                uow=uow,
                tools=tools,
                maintainers=maintainers,
                versions=versions,
                locks=PostgreSQLDraftLockRepository(session),
                clock=clock,
                id_generator=id_generator,
            ),
        )
        return await fixture.ensure(export=export)


def format_staging_proof_fixture_summary(result: StagingProofFixtureResult) -> str:
    """Return the operator-facing one-line fixture summary (no account data)."""
    return (
        "Staging proof fixture ok: "
        f"tool_slug={result.tool_slug}, "
        f"tool_id={result.tool_id}, "
        f"draft_version_id={result.draft_version_id}, "
        f"created_tool={result.created_tool}, "
        f"assigned_maintainer={result.assigned_maintainer}, "
        f"created_draft={result.created_draft}"
    )
