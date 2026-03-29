"""CLI commands for validating and importing domain allowlist seed files.

Purpose:
  Give operators a deterministic dry-run and import path for the curated
  Swedish school-sector domain CSVs.

Relationships:
  - Uses `DomainAllowlistImporter` for CSV validation and DB upserts.
  - Reuses the regular SQLAlchemy session/UoW stack instead of ad hoc SQL.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer

from skriptoteket.application.identity.domain_allowlist_import import (
    DomainAllowlistImporter,
    DomainAllowlistImportRun,
)
from skriptoteket.application.identity.domain_validator import TldextractDomainValidator
from skriptoteket.cli._db import open_session
from skriptoteket.config import Settings
from skriptoteket.infrastructure.clock import UTCClock
from skriptoteket.infrastructure.db.uow import SQLAlchemyUnitOfWork
from skriptoteket.infrastructure.repositories.allowed_domain_repository import (
    PostgreSQLAllowedDomainRepository,
)
from skriptoteket.infrastructure.repositories.blocked_domain_repository import (
    PostgreSQLBlockedDomainRepository,
)

DEFAULT_ALLOWED_MUNICIPALITIES_CSV = Path("data/identity/allowed_domains_municipalities.csv")
DEFAULT_ALLOWED_ENSKILDA_CSV = Path("data/identity/allowed_domains_enskilda_huvudman.csv")
DEFAULT_BLOCKED_CSV = Path("data/identity/blocked_domains.csv")


def validate_domain_allowlist(
    municipalities_csv: Path = typer.Option(
        DEFAULT_ALLOWED_MUNICIPALITIES_CSV,
        help="Municipality allowlist CSV.",
    ),
    enskilda_csv: Path = typer.Option(
        DEFAULT_ALLOWED_ENSKILDA_CSV,
        help="Enskild-huvudman allowlist CSV.",
    ),
    blocked_csv: Path = typer.Option(
        DEFAULT_BLOCKED_CSV,
        help="Blocked-domain CSV.",
    ),
) -> None:
    """Validate the current CSV contract without writing to the database."""
    asyncio.run(
        _run_domain_allowlist_import(
            municipalities_csv=municipalities_csv,
            enskilda_csv=enskilda_csv,
            blocked_csv=blocked_csv,
            dry_run=True,
            validate_only=True,
        )
    )


def import_domain_allowlist(
    municipalities_csv: Path = typer.Option(
        DEFAULT_ALLOWED_MUNICIPALITIES_CSV,
        help="Municipality allowlist CSV.",
    ),
    enskilda_csv: Path = typer.Option(
        DEFAULT_ALLOWED_ENSKILDA_CSV,
        help="Enskild-huvudman allowlist CSV.",
    ),
    blocked_csv: Path = typer.Option(
        DEFAULT_BLOCKED_CSV,
        help="Blocked-domain CSV.",
    ),
    dry_run: bool = typer.Option(
        True,
        "--dry-run/--apply",
        help="Preview changes without writing (default: dry-run).",
    ),
) -> None:
    """Validate and import the current domain allowlist seed files."""
    asyncio.run(
        _run_domain_allowlist_import(
            municipalities_csv=municipalities_csv,
            enskilda_csv=enskilda_csv,
            blocked_csv=blocked_csv,
            dry_run=dry_run,
            validate_only=False,
        )
    )


async def _run_domain_allowlist_import(
    *,
    municipalities_csv: Path,
    enskilda_csv: Path,
    blocked_csv: Path,
    dry_run: bool,
    validate_only: bool,
) -> None:
    settings = Settings()
    async with open_session(settings) as session:
        allowed_domains = PostgreSQLAllowedDomainRepository(session)
        blocked_domains = PostgreSQLBlockedDomainRepository(session)
        importer = DomainAllowlistImporter(
            uow=SQLAlchemyUnitOfWork(session),
            allowed_domains=allowed_domains,
            blocked_domains=blocked_domains,
            domain_validator=TldextractDomainValidator(
                allowed_domains=allowed_domains,
                blocked_domains=blocked_domains,
            ),
            clock=UTCClock(),
        )
        run = await importer.run(
            allowed_files=(municipalities_csv, enskilda_csv),
            blocked_files=(blocked_csv,),
            dry_run=dry_run,
        )

    _print_summary(run=run, validate_only=validate_only)
    if run.has_errors:
        raise SystemExit("Domain allowlist validation failed.")


def _print_summary(*, run: DomainAllowlistImportRun, validate_only: bool) -> None:
    action = "validation" if validate_only else ("dry-run" if run.allowed.dry_run else "import")
    typer.echo(f"Domain allowlist {action} summary")
    _print_section(run.allowed)
    _print_section(run.blocked)


def _print_section(summary) -> None:
    typer.echo(
        f"- {summary.label}: "
        f"total={summary.total_rows} "
        f"inserted={summary.inserted} "
        f"updated={summary.updated} "
        f"unchanged={summary.unchanged} "
        f"rejected={summary.rejected}"
    )
    for rejected in summary.rejected_rows[:10]:
        typer.echo(
            f"  reject {rejected.file_path}:{rejected.line_number} "
            f"domain={rejected.domain or '<none>'} "
            f"reason={rejected.reason}"
        )
    if summary.rejected > 10:
        typer.echo(f"  ... and {summary.rejected - 10} more rejected rows")
