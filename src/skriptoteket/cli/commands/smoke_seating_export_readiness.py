"""CLI smoke gate for production seating-export readiness.

Purpose:
    Create one real Klassrumskartan seating export job, wait for terminal
    success through the callback path (without polling the export-job read API),
    and prove Vault-backed download delivery from the persisted artifact.

Relationships:
    - Uses classroom-planner application handlers and repositories directly
      inside the production web runtime.
    - Consumed by `scripts/hemma_deploy_and_verify_seating_export.sh` as the
      hard post-deploy export smoke for PR-0122.
"""

from __future__ import annotations

import asyncio
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import typer

from skriptoteket.application.curated_apps.classroom_planner.exports import (
    SeatingExportJobStatus,
    SeatingExportKind,
    SeatingExportLayoutId,
    SeatingExportPaperSize,
)
from skriptoteket.application.curated_apps.classroom_planner.handlers import (
    seating_export_job_completion as seating_export_job_completion_handlers,
)
from skriptoteket.application.curated_apps.classroom_planner.handlers.drafts import (
    PatchDraftHandler,
)
from skriptoteket.application.curated_apps.classroom_planner.handlers.rosters import (
    CreateRosterHandler,
    UpdateRosterHandler,
)
from skriptoteket.application.curated_apps.classroom_planner.handlers.seating_drafts import (
    CreateSeatingDraftHandler,
)
from skriptoteket.application.curated_apps.classroom_planner.handlers.seating_export_jobs import (
    CreateSeatingExportJobHandler,
)
from skriptoteket.application.curated_apps.classroom_planner.handlers.seating_exports import (
    PrepareSeatingExportHandler,
)
from skriptoteket.application.curated_apps.classroom_planner.handlers.templates import (
    CreateRoomTemplateHandler,
    UpdateRoomTemplateHandler,
)
from skriptoteket.cli._db import open_session
from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.classroom_planner.models import (
    DEFAULT_ROOM_GRID_COLS,
    DEFAULT_ROOM_GRID_ROWS,
    Seat,
    SeatAssignment,
    Student,
)
from skriptoteket.domain.errors import DomainError
from skriptoteket.domain.identity.models import User
from skriptoteket.infrastructure.clock import UTCClock
from skriptoteket.infrastructure.curated_apps.apps.classroom_planner.poster_renderer import (
    BrutalistPosterRenderer,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.sir_convert_client_v2 import (
    SirConvertALotClientV2,
    SirConvertClientSettingsV2,
)
from skriptoteket.infrastructure.db.uow import SQLAlchemyUnitOfWork
from skriptoteket.infrastructure.id_generator import UUID4Generator
from skriptoteket.infrastructure.repositories.classroom_planner import (
    PostgreSQLPlanDraftRepository,
    PostgreSQLRoomTemplateRepository,
    PostgreSQLRosterRepository,
)
from skriptoteket.infrastructure.repositories.classroom_planner_export_jobs import (
    PostgreSQLSeatingExportJobRepository,
)
from skriptoteket.infrastructure.repositories.classroom_planner_export_webhook_bindings import (
    PostgreSQLSeatingExportWebhookBindingRepository,
)
from skriptoteket.infrastructure.repositories.user_repository import PostgreSQLUserRepository
from skriptoteket.infrastructure.repositories.user_vault_file_repository import (
    PostgreSQLUserVaultFileRepository,
)
from skriptoteket.infrastructure.vault.local_vault_storage import LocalVaultStorage

_SMOKE_ROSTER_NAME = "PR-0122 Hemma seating export smoke"
_SMOKE_TEMPLATE_NAME = "PR-0122 Hemma seating export smoke"
_SMOKE_STUDENTS = (
    Student(id="smoke-student-1", display_name="Export Smoke Elev 1"),
    Student(id="smoke-student-2", display_name="Export Smoke Elev 2"),
)
_SMOKE_SEATS = (
    Seat(id="smoke-seat-1", x=2, y=2),
    Seat(id="smoke-seat-2", x=5, y=2),
)


@dataclass(frozen=True, slots=True)
class _SmokeContext:
    actor_id: UUID
    actor_email: str
    draft_id: UUID
    export_job_id: UUID
    vault_file_id: UUID
    filename: str
    pdf_bytes: int
    correlation_id: str


def smoke_seating_export_readiness(
    timeout_seconds: int = typer.Option(
        180,
        min=10,
        help="Maximum time to wait for callback-driven terminal export success.",
    ),
    poll_interval_seconds: float = typer.Option(
        2.0,
        min=0.5,
        help="How often to poll the database for callback completion.",
    ),
    correlation_id: str | None = typer.Option(
        None,
        help="Optional correlation id to stamp onto the smoke export flow.",
    ),
) -> None:
    """Run the production callback-capable seating-export smoke gate."""

    asyncio.run(
        _smoke_seating_export_readiness_async(
            timeout_seconds=timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
            correlation_id=correlation_id,
        )
    )


async def _smoke_seating_export_readiness_async(
    *,
    timeout_seconds: int,
    poll_interval_seconds: float,
    correlation_id: str | None,
) -> None:
    settings = Settings()
    bootstrap_email = os.environ.get("BOOTSTRAP_SUPERUSER_EMAIL", "").strip()
    if bootstrap_email == "":
        raise SystemExit("Missing BOOTSTRAP_SUPERUSER_EMAIL for the seating export smoke.")

    effective_correlation_id = correlation_id or f"seat-export-smoke-{uuid4()}"
    actor = await _load_actor_by_email(
        settings=settings,
        email=bootstrap_email,
    )
    roster_id, template_id = await _ensure_smoke_assets(settings=settings, actor=actor)
    draft_id = await _create_smoke_draft(
        settings=settings,
        actor=actor,
        roster_id=roster_id,
        template_id=template_id,
    )
    await _assign_first_student_to_first_seat(
        settings=settings,
        actor=actor,
        draft_id=draft_id,
    )
    export_job_id = await _create_export_job(
        settings=settings,
        actor=actor,
        draft_id=draft_id,
        correlation_id=effective_correlation_id,
    )
    terminal_job = await _wait_for_callback_completion(
        settings=settings,
        actor_id=actor.id,
        export_job_id=export_job_id,
        timeout_seconds=timeout_seconds,
        poll_interval_seconds=poll_interval_seconds,
    )
    filename, content = await _download_export_from_vault(
        settings=settings,
        actor=actor,
        export_job_id=export_job_id,
    )

    if not content.startswith(b"%PDF"):
        raise SystemExit(
            "Seating export smoke downloaded a file that does not look like a PDF from Vault."
        )

    summary = _SmokeContext(
        actor_id=actor.id,
        actor_email=actor.email,
        draft_id=draft_id,
        export_job_id=export_job_id,
        vault_file_id=terminal_job.vault_file_id,
        filename=filename,
        pdf_bytes=len(content),
        correlation_id=effective_correlation_id,
    )
    typer.echo(
        json.dumps(
            asdict(summary),
            default=str,
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )
    )


async def _load_actor_by_email(*, settings: Settings, email: str) -> User:
    async with open_session(settings) as session:
        users = PostgreSQLUserRepository(session)
        user_auth = await users.get_auth_by_email(email)
    if user_auth is None:
        raise SystemExit(
            "Bootstrap superuser not found for the seating export smoke. "
            "Run bootstrap-superuser first."
        )
    return user_auth.user


async def _ensure_smoke_assets(*, settings: Settings, actor: User) -> tuple[UUID, UUID]:
    async with open_session(settings) as session:
        rosters = PostgreSQLRosterRepository(session)
        templates = PostgreSQLRoomTemplateRepository(session)
        existing_roster = next(
            (
                roster
                for roster in await rosters.list_by_owner(owner_user_id=actor.id)
                if roster.name == _SMOKE_ROSTER_NAME
            ),
            None,
        )
        existing_template = next(
            (
                template
                for template in await templates.list_by_owner(owner_user_id=actor.id)
                if template.name == _SMOKE_TEMPLATE_NAME
            ),
            None,
        )

        uow = SQLAlchemyUnitOfWork(session)
        clock = UTCClock()
        id_generator = UUID4Generator()

        if existing_roster is None:
            create_roster = CreateRosterHandler(
                uow=uow,
                rosters=rosters,
                clock=clock,
                id_generator=id_generator,
            )
            existing_roster = await create_roster.handle(
                owner_user_id=actor.id,
                name=_SMOKE_ROSTER_NAME,
                students=list(_SMOKE_STUDENTS),
            )
        elif not _matches_expected_smoke_roster(existing_roster):
            update_roster = UpdateRosterHandler(
                uow=uow,
                rosters=rosters,
                clock=clock,
            )
            existing_roster = await update_roster.handle(
                roster_id=existing_roster.id,
                owner_user_id=actor.id,
                name=_SMOKE_ROSTER_NAME,
                students=list(_SMOKE_STUDENTS),
            )

        if existing_template is None:
            create_template = CreateRoomTemplateHandler(
                uow=uow,
                templates=templates,
                clock=clock,
                id_generator=id_generator,
            )
            existing_template = await create_template.handle(
                owner_user_id=actor.id,
                name=_SMOKE_TEMPLATE_NAME,
                seats=list(_SMOKE_SEATS),
                fixtures=[],
            )
        elif not _matches_expected_smoke_template(existing_template):
            update_template = UpdateRoomTemplateHandler(
                uow=uow,
                templates=templates,
                clock=clock,
            )
            existing_template = await update_template.handle(
                template_id=existing_template.id,
                owner_user_id=actor.id,
                name=_SMOKE_TEMPLATE_NAME,
                grid_cols=DEFAULT_ROOM_GRID_COLS,
                grid_rows=DEFAULT_ROOM_GRID_ROWS,
                seats=list(_SMOKE_SEATS),
                fixtures=[],
            )

        return existing_roster.id, existing_template.id


def _matches_expected_smoke_roster(roster) -> bool:
    """Return whether one smoke roster still matches the canonical student IDs."""

    actual_students = tuple((student.id, student.display_name) for student in roster.students)
    expected_students = tuple((student.id, student.display_name) for student in _SMOKE_STUDENTS)
    return actual_students == expected_students


def _matches_expected_smoke_template(template) -> bool:
    """Return whether one smoke template still matches the canonical seat map."""

    actual_seats = tuple((seat.id, seat.x, seat.y) for seat in template.seats)
    expected_seats = tuple((seat.id, seat.x, seat.y) for seat in _SMOKE_SEATS)
    return (
        template.grid_cols == DEFAULT_ROOM_GRID_COLS
        and template.grid_rows == DEFAULT_ROOM_GRID_ROWS
        and actual_seats == expected_seats
        and template.fixtures == []
    )


async def _create_smoke_draft(
    *,
    settings: Settings,
    actor: User,
    roster_id: UUID,
    template_id: UUID,
) -> UUID:
    async with open_session(settings) as session:
        create_draft = CreateSeatingDraftHandler(
            uow=SQLAlchemyUnitOfWork(session),
            rosters=PostgreSQLRosterRepository(session),
            templates=PostgreSQLRoomTemplateRepository(session),
            drafts=PostgreSQLPlanDraftRepository(session),
            clock=UTCClock(),
            id_generator=UUID4Generator(),
        )
        draft = await create_draft.handle(
            owner_user_id=actor.id,
            roster_id=roster_id,
            template_id=template_id,
        )
    return draft.id


async def _assign_first_student_to_first_seat(
    *,
    settings: Settings,
    actor: User,
    draft_id: UUID,
) -> None:
    async with open_session(settings) as session:
        patch_draft = PatchDraftHandler(
            uow=SQLAlchemyUnitOfWork(session),
            drafts=PostgreSQLPlanDraftRepository(session),
            rosters=PostgreSQLRosterRepository(session),
            templates=PostgreSQLRoomTemplateRepository(session),
            clock=UTCClock(),
        )
        await patch_draft.handle(
            draft_id=draft_id,
            owner_user_id=actor.id,
            expected_revision=0,
            seat_assignments=[
                SeatAssignment(
                    student_id=_SMOKE_STUDENTS[0].id,
                    seat_id=_SMOKE_SEATS[0].id,
                )
            ],
        )


async def _create_export_job(
    *,
    settings: Settings,
    actor: User,
    draft_id: UUID,
    correlation_id: str,
) -> UUID:
    client_settings = SirConvertClientSettingsV2(
        base_url=settings.SIR_CONVERT_A_LOT_V2_BASE_URL,
        api_key=settings.SIR_CONVERT_A_LOT_V2_API_KEY,
        timeout_seconds=settings.SIR_CONVERT_A_LOT_V2_TIMEOUT_SECONDS,
    )
    async with open_session(settings) as session:
        async with httpx.AsyncClient(
            base_url=client_settings.base_url,
            timeout=client_settings.timeout_seconds,
        ) as http_client:
            create_job = CreateSeatingExportJobHandler(
                prepare=PrepareSeatingExportHandler(
                    drafts=PostgreSQLPlanDraftRepository(session),
                    rosters=PostgreSQLRosterRepository(session),
                    templates=PostgreSQLRoomTemplateRepository(session),
                ),
                jobs=PostgreSQLSeatingExportJobRepository(session),
                webhook_bindings=PostgreSQLSeatingExportWebhookBindingRepository(session),
                renderer=BrutalistPosterRenderer(),
                client=SirConvertALotClientV2(
                    settings=client_settings,
                    client=http_client,
                ),
                uow=SQLAlchemyUnitOfWork(session),
                clock=UTCClock(),
                id_generator=UUID4Generator(),
                settings=settings,
            )
            result = await create_job.handle(
                actor=actor,
                draft_id=draft_id,
                export_kind=SeatingExportKind.PDF,
                layout_id=SeatingExportLayoutId.PRETTY_BRUTALIST_POSTER,
                paper_size=SeatingExportPaperSize.A3_LANDSCAPE,
                correlation_id=correlation_id,
            )
    return result.job_id


async def _wait_for_callback_completion(
    *,
    settings: Settings,
    actor_id: UUID,
    export_job_id: UUID,
    timeout_seconds: int,
    poll_interval_seconds: float,
):
    deadline = asyncio.get_running_loop().time() + timeout_seconds
    while True:
        async with open_session(settings) as session:
            jobs = PostgreSQLSeatingExportJobRepository(session)
            job = await jobs.get_by_id(job_id=export_job_id)
        if job is None or job.owner_user_id != actor_id:
            raise SystemExit("Seating export smoke lost the export job before completion.")
        if job.status is SeatingExportJobStatus.SUCCEEDED and job.vault_file_id is not None:
            return job
        if job.status is SeatingExportJobStatus.FAILED:
            raise SystemExit(
                f"Seating export smoke failed before Vault download: status={job.status.value} "
                f"error={job.error_message!r}"
            )
        if asyncio.get_running_loop().time() >= deadline:
            raise SystemExit(
                "Seating export smoke timed out waiting for callback-driven terminal success."
            )
        await asyncio.sleep(poll_interval_seconds)


async def _download_export_from_vault(
    *,
    settings: Settings,
    actor: User,
    export_job_id: UUID,
) -> tuple[str, bytes]:
    async with open_session(settings) as session:
        download_handler = seating_export_job_completion_handlers.DownloadSeatingExportJobHandler(
            jobs=PostgreSQLSeatingExportJobRepository(session),
            vault_files=PostgreSQLUserVaultFileRepository(session),
            vault_storage=LocalVaultStorage(vault_root=Path(settings.VAULT_ROOT)),
            uow=SQLAlchemyUnitOfWork(session),
        )
        try:
            return await download_handler.handle(actor=actor, job_id=export_job_id)
        except DomainError as exc:
            raise SystemExit(exc.message) from exc
