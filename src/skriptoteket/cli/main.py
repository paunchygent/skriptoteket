from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from importlib.resources import files as resource_files
from pathlib import Path

import typer
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from skriptoteket.application.catalog.commands import PublishToolCommand, UpdateToolMetadataCommand
from skriptoteket.application.catalog.handlers.publish_tool import PublishToolHandler
from skriptoteket.application.catalog.handlers.update_tool_metadata import UpdateToolMetadataHandler
from skriptoteket.application.identity.authentication import authenticate_local_user
from skriptoteket.application.identity.commands import CreateLocalUserCommand
from skriptoteket.application.identity.handlers.create_local_user import CreateLocalUserHandler
from skriptoteket.application.identity.handlers.provision_local_user import (
    ProvisionLocalUserHandler,
)
from skriptoteket.application.scripting.commands import (
    CreateDraftVersionCommand,
    PublishVersionCommand,
    SubmitForReviewCommand,
)
from skriptoteket.application.scripting.handlers.create_draft_version import (
    CreateDraftVersionHandler,
)
from skriptoteket.application.scripting.handlers.publish_version import PublishVersionHandler
from skriptoteket.application.scripting.handlers.submit_for_review import SubmitForReviewHandler
from skriptoteket.config import Settings
from skriptoteket.domain.catalog.models import Tool, update_tool_metadata
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role
from skriptoteket.infrastructure.clock import UTCClock
from skriptoteket.infrastructure.db.uow import SQLAlchemyUnitOfWork
from skriptoteket.infrastructure.id_generator import UUID4Generator
from skriptoteket.infrastructure.repositories.category_repository import (
    PostgreSQLCategoryRepository,
)
from skriptoteket.infrastructure.repositories.profession_repository import (
    PostgreSQLProfessionRepository,
)
from skriptoteket.infrastructure.repositories.profile_repository import (
    PostgreSQLProfileRepository,
)
from skriptoteket.infrastructure.repositories.tool_maintainer_repository import (
    PostgreSQLToolMaintainerRepository,
)
from skriptoteket.infrastructure.repositories.tool_repository import PostgreSQLToolRepository
from skriptoteket.infrastructure.repositories.tool_version_repository import (
    PostgreSQLToolVersionRepository,
)
from skriptoteket.infrastructure.repositories.user_repository import PostgreSQLUserRepository
from skriptoteket.infrastructure.runner.retention import prune_artifacts_root
from skriptoteket.infrastructure.security.password_hasher import Argon2PasswordHasher
from skriptoteket.script_bank.bank import SCRIPT_BANK

app = typer.Typer(no_args_is_help=True)


@app.command()
def bootstrap_superuser(
    email: str = typer.Option(..., prompt=True),
    password: str = typer.Option(..., prompt=True, hide_input=True, confirmation_prompt=True),
) -> None:
    """Create the first superuser (admin-provisioned accounts; no self-signup)."""
    asyncio.run(_bootstrap_superuser_async(email=email, password=password))


async def _bootstrap_superuser_async(*, email: str, password: str) -> None:
    settings = Settings()
    engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    try:
        async with sessionmaker() as session:
            uow = SQLAlchemyUnitOfWork(session)
            users = PostgreSQLUserRepository(session)
            profiles = PostgreSQLProfileRepository(session)
            handler = CreateLocalUserHandler(
                settings=settings,
                uow=uow,
                users=users,
                profiles=profiles,
                password_hasher=Argon2PasswordHasher(),
                clock=UTCClock(),
                id_generator=UUID4Generator(),
            )

            try:
                result = await handler.handle(
                    CreateLocalUserCommand(email=email, password=password, role=Role.SUPERUSER)
                )
            except DomainError as exc:
                if exc.code == ErrorCode.DUPLICATE_ENTRY:
                    raise SystemExit("User already exists for that email.") from exc
                raise

        typer.echo(f"Created superuser: {result.user.email} ({result.user.id})")
    finally:
        await engine.dispose()


@app.command()
def provision_user(
    actor_email: str = typer.Option(..., prompt=True),
    actor_password: str = typer.Option(..., prompt=True, hide_input=True),
    email: str = typer.Option(..., prompt=True),
    password: str = typer.Option(..., prompt=True, hide_input=True, confirmation_prompt=True),
    role: Role = typer.Option(Role.USER),
) -> None:
    """Provision a local user (requires an admin/superuser account)."""
    asyncio.run(
        _provision_user_async(
            actor_email=actor_email,
            actor_password=actor_password,
            email=email,
            password=password,
            role=role,
        )
    )


async def _provision_user_async(
    *,
    actor_email: str,
    actor_password: str,
    email: str,
    password: str,
    role: Role,
) -> None:
    settings = Settings()
    engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    try:
        async with sessionmaker() as session:
            uow = SQLAlchemyUnitOfWork(session)
            users = PostgreSQLUserRepository(session)
            profiles = PostgreSQLProfileRepository(session)
            password_hasher = Argon2PasswordHasher()

            try:
                actor = await authenticate_local_user(
                    users=users,
                    password_hasher=password_hasher,
                    email=actor_email,
                    password=actor_password,
                )
            except DomainError as exc:
                if exc.code == ErrorCode.INVALID_CREDENTIALS:
                    raise SystemExit("Invalid admin credentials.") from exc
                raise

            handler = ProvisionLocalUserHandler(
                uow=uow,
                users=users,
                profiles=profiles,
                password_hasher=password_hasher,
                clock=UTCClock(),
                id_generator=UUID4Generator(),
            )

            try:
                result = await handler.handle(
                    actor=actor,
                    command=CreateLocalUserCommand(email=email, password=password, role=role),
                )
            except DomainError as exc:
                if exc.code == ErrorCode.DUPLICATE_ENTRY:
                    raise SystemExit("User already exists for that email.") from exc
                if exc.code == ErrorCode.FORBIDDEN:
                    raise SystemExit("Insufficient permissions to provision that user.") from exc
                raise

        typer.echo(
            f"Created user: {result.user.email} ({result.user.role.value}) ({result.user.id})"
        )
    finally:
        await engine.dispose()


@app.command()
def prune_artifacts(
    retention_days: int | None = typer.Option(None, help="Override ARTIFACTS_RETENTION_DAYS"),
    artifacts_root: Path | None = typer.Option(None, help="Override ARTIFACTS_ROOT"),
    dry_run: bool = typer.Option(False),
) -> None:
    """Delete artifact run directories older than N days (cron-friendly)."""
    settings = Settings()
    effective_root = settings.ARTIFACTS_ROOT if artifacts_root is None else artifacts_root
    effective_days = settings.ARTIFACTS_RETENTION_DAYS if retention_days is None else retention_days

    if dry_run:
        typer.echo(
            "Dry run: would prune artifact directories under "
            f"{effective_root} older than {effective_days} days."
        )
        raise SystemExit(0)

    deleted = prune_artifacts_root(
        artifacts_root=effective_root,
        retention_days=effective_days,
        now=datetime.now(timezone.utc),
    )
    typer.echo(f"Deleted {deleted} artifact run directories from {effective_root}.")


@app.command()
def seed_script_bank(
    actor_email: str = typer.Option(
        ...,
        envvar=["SKRIPTOTEKET_SCRIPT_BANK_ACTOR_EMAIL", "BOOTSTRAP_SUPERUSER_EMAIL"],
        prompt=True,
        help=(
            "Admin/superuser email for audit fields. "
            "Use BOOTSTRAP_SUPERUSER_EMAIL from the SERVER's .env (e.g. admin@hule.education)."
        ),
    ),
    actor_password: str = typer.Option(
        ...,
        envvar=["SKRIPTOTEKET_SCRIPT_BANK_ACTOR_PASSWORD", "BOOTSTRAP_SUPERUSER_PASSWORD"],
        prompt=True,
        hide_input=True,
        help=(
            "Password for the admin/superuser account. "
            "Use BOOTSTRAP_SUPERUSER_PASSWORD from the SERVER's .env."
        ),
    ),
    slug: list[str] = typer.Option(
        [],
        "--slug",
        help="Seed only these tool slugs (repeatable). Defaults to all script-bank entries.",
    ),
    publish: bool = typer.Option(
        True,
        help="Ensure seeded tools are published (visible in Katalog) if an ACTIVE version exists.",
    ),
    sync_metadata: bool = typer.Option(
        False,
        help="Update title/summary for existing tools to match the repo script bank.",
    ),
    sync_code: bool = typer.Option(
        False,
        help=(
            "If the ACTIVE version differs, create + publish a new version from the repo "
            "script bank."
        ),
    ),
    dry_run: bool = typer.Option(
        False,
        help="Print planned actions without writing to the database.",
    ),
) -> None:
    """Seed curated repo scripts into the database (idempotent by tool slug).

    This command must be run ON THE SERVER or inside the Docker container where
    the database is accessible. The superuser credentials are stored in the server's
    .env file (BOOTSTRAP_SUPERUSER_EMAIL and BOOTSTRAP_SUPERUSER_PASSWORD).

    Example (SSH into server):
        ssh hemma
        cd ~/apps/skriptoteket
        docker exec -e PYTHONPATH=/app/src skriptoteket-web \\
            pdm run python -m skriptoteket.cli seed-script-bank --dry-run
    """
    asyncio.run(
        _seed_script_bank_async(
            actor_email=actor_email,
            actor_password=actor_password,
            slugs=slug,
            publish=publish,
            sync_metadata=sync_metadata,
            sync_code=sync_code,
            dry_run=dry_run,
        )
    )


async def _seed_script_bank_async(
    *,
    actor_email: str,
    actor_password: str,
    slugs: list[str],
    publish: bool,
    sync_metadata: bool,
    sync_code: bool,
    dry_run: bool,
) -> None:
    settings = Settings()
    engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
    sessionmaker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    try:
        async with sessionmaker() as session:
            uow = SQLAlchemyUnitOfWork(session)
            users = PostgreSQLUserRepository(session)
            password_hasher = Argon2PasswordHasher()
            actor = await authenticate_local_user(
                users=users,
                password_hasher=password_hasher,
                email=actor_email,
                password=actor_password,
            )
            if actor.role not in {Role.ADMIN, Role.SUPERUSER}:
                raise SystemExit("Insufficient permissions: actor must be admin or superuser.")

            clock = UTCClock()
            id_generator = UUID4Generator()

            tools = PostgreSQLToolRepository(session)
            maintainers = PostgreSQLToolMaintainerRepository(session)
            versions = PostgreSQLToolVersionRepository(session)
            professions = PostgreSQLProfessionRepository(session)
            categories = PostgreSQLCategoryRepository(session)

            create_draft_version = CreateDraftVersionHandler(
                uow=uow,
                tools=tools,
                maintainers=maintainers,
                versions=versions,
                clock=clock,
                id_generator=id_generator,
            )
            submit_for_review = SubmitForReviewHandler(
                uow=uow,
                versions=versions,
                maintainers=maintainers,
                clock=clock,
            )
            publish_version = PublishVersionHandler(
                uow=uow,
                tools=tools,
                versions=versions,
                clock=clock,
                id_generator=id_generator,
            )
            publish_tool_handler = PublishToolHandler(
                uow=uow,
                tools=tools,
                versions=versions,
                clock=clock,
            )
            update_tool_metadata_handler = UpdateToolMetadataHandler(
                uow=uow,
                tools=tools,
                clock=clock,
            )

            slug_set = set(slugs)
            selected_entries = (
                [entry for entry in SCRIPT_BANK if entry.slug in slug_set] if slugs else SCRIPT_BANK
            )
            if slugs and not selected_entries:
                raise SystemExit(f"No script-bank entries found for slugs: {', '.join(slugs)}")

            for entry in selected_entries:
                await _seed_one_entry(
                    actor=actor,
                    entry=entry,
                    uow=uow,
                    tools=tools,
                    versions=versions,
                    professions=professions,
                    categories=categories,
                    create_draft_version=create_draft_version,
                    submit_for_review=submit_for_review,
                    publish_version=publish_version,
                    publish_tool=publish_tool_handler,
                    update_tool_metadata_handler=update_tool_metadata_handler,
                    sync_metadata=sync_metadata,
                    sync_code=sync_code,
                    publish=publish,
                    dry_run=dry_run,
                )
    finally:
        await engine.dispose()


def _normalize_seed_text(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(value.split()).casefold()


async def _find_tool_by_title_summary(
    *,
    tools: PostgreSQLToolRepository,
    title: str,
    summary: str | None,
) -> Tool | None:
    normalized_title = _normalize_seed_text(title)
    normalized_summary = _normalize_seed_text(summary)

    if not normalized_title:
        return None

    candidates = await tools.list_all()
    matches = [
        candidate
        for candidate in candidates
        if _normalize_seed_text(candidate.title) == normalized_title
        and _normalize_seed_text(candidate.summary) == normalized_summary
    ]

    if len(matches) > 1:
        slugs = ", ".join(sorted({candidate.slug for candidate in matches}))
        raise SystemExit(
            "Duplicate tools found with matching title+summary. "
            f"Resolve duplicates before seeding. Slugs: {slugs}"
        )

    return matches[0] if matches else None


async def _seed_one_entry(
    *,
    actor,
    entry,
    uow: SQLAlchemyUnitOfWork,
    tools: PostgreSQLToolRepository,
    versions: PostgreSQLToolVersionRepository,
    professions: PostgreSQLProfessionRepository,
    categories: PostgreSQLCategoryRepository,
    create_draft_version: CreateDraftVersionHandler,
    submit_for_review: SubmitForReviewHandler,
    publish_version: PublishVersionHandler,
    publish_tool: PublishToolHandler,
    update_tool_metadata_handler: UpdateToolMetadataHandler,
    sync_metadata: bool,
    sync_code: bool,
    publish: bool,
    dry_run: bool,
) -> None:
    now = UTCClock().now()
    tool = await tools.get_by_slug(slug=entry.slug)
    created = False
    deduped_from_slug: str | None = None

    if tool is None:
        dedupe_match = await _find_tool_by_title_summary(
            tools=tools,
            title=entry.title,
            summary=entry.summary,
        )
        if dedupe_match is not None:
            tool = dedupe_match
            deduped_from_slug = entry.slug
            typer.echo(f"Seed dedupe: using existing tool '{tool.slug}' for entry '{entry.slug}'.")
        else:
            tool = None

    if tool is None:
        profession_ids = []
        for profession_slug in entry.profession_slugs:
            profession = await professions.get_by_slug(profession_slug)
            if profession is None:
                raise SystemExit(f"Unknown profession slug: {profession_slug}")
            profession_ids.append(profession.id)

        category_ids = []
        for category_slug in entry.category_slugs:
            category = await categories.get_by_slug(category_slug)
            if category is None:
                raise SystemExit(f"Unknown category slug: {category_slug}")
            category_ids.append(category.id)

        draft_tool = Tool(
            id=UUID4Generator().new_uuid(),
            owner_user_id=actor.id,
            slug=entry.slug,
            title=entry.title,
            summary=entry.summary,
            is_published=False,
            active_version_id=None,
            created_at=now,
            updated_at=now,
        )
        normalized_tool = update_tool_metadata(
            tool=draft_tool,
            title=draft_tool.title,
            summary=draft_tool.summary,
            now=now,
        )

        if dry_run:
            typer.echo(f"[dry-run] Create tool: {entry.slug}")
        else:
            async with uow:
                tool = await tools.create_draft(
                    tool=normalized_tool,
                    profession_ids=profession_ids,
                    category_ids=category_ids,
                )
            created = True
    else:
        if sync_metadata and (tool.title != entry.title or tool.summary != entry.summary):
            if dry_run:
                typer.echo(f"[dry-run] Update metadata: {entry.slug}")
            else:
                await update_tool_metadata_handler.handle(
                    actor=actor,
                    command=UpdateToolMetadataCommand(
                        tool_id=tool.id,
                        title=entry.title,
                        summary=entry.summary,
                    ),
                )
                tool = await tools.get_by_id(tool_id=tool.id)
                if tool is None:
                    raise SystemExit(f"Tool disappeared during seed: {entry.slug}")

    assert tool is not None

    source_code = (
        resource_files("skriptoteket.script_bank.scripts") / entry.source_filename
    ).read_text(encoding="utf-8")

    active_version = await versions.get_active_for_tool(tool_id=tool.id)
    if active_version is None:
        if dry_run:
            typer.echo(f"[dry-run] Create + publish initial version: {entry.slug}")
        else:
            draft_result = await create_draft_version.handle(
                actor=actor,
                command=CreateDraftVersionCommand(
                    tool_id=tool.id,
                    entrypoint=entry.entrypoint,
                    source_code=source_code,
                    usage_instructions=entry.usage_instructions,
                    change_summary="Seed: initial version från repo",
                ),
            )
            submitted = await submit_for_review.handle(
                actor=actor,
                command=SubmitForReviewCommand(
                    version_id=draft_result.version.id,
                    review_note="Automatiskt seedad från repo script bank.",
                ),
            )
            await publish_version.handle(
                actor=actor,
                command=PublishVersionCommand(
                    version_id=submitted.version.id,
                    change_summary="Automatiskt publicerad från repo script bank.",
                ),
            )
    elif sync_code and (
        active_version.entrypoint != entry.entrypoint
        or active_version.source_code != source_code
        or active_version.usage_instructions != entry.usage_instructions
    ):
        if dry_run:
            typer.echo(f"[dry-run] Create + publish updated version: {entry.slug}")
        else:
            draft_result = await create_draft_version.handle(
                actor=actor,
                command=CreateDraftVersionCommand(
                    tool_id=tool.id,
                    derived_from_version_id=active_version.id,
                    entrypoint=entry.entrypoint,
                    source_code=source_code,
                    usage_instructions=entry.usage_instructions,
                    change_summary="Seed: uppdaterad version från repo",
                ),
            )
            submitted = await submit_for_review.handle(
                actor=actor,
                command=SubmitForReviewCommand(
                    version_id=draft_result.version.id,
                    review_note="Automatiskt uppdaterad från repo script bank.",
                ),
            )
            await publish_version.handle(
                actor=actor,
                command=PublishVersionCommand(
                    version_id=submitted.version.id,
                    change_summary="Automatiskt publicerad (uppdatering) från repo script bank.",
                ),
            )

    tool = await tools.get_by_id(tool_id=tool.id)
    if tool is None:
        raise SystemExit(f"Tool disappeared during seed: {entry.slug}")

    if publish and not tool.is_published:
        if dry_run:
            typer.echo(f"[dry-run] Publish tool: {tool.slug}")
        else:
            await publish_tool.handle(actor=actor, command=PublishToolCommand(tool_id=tool.id))

    if created and not dry_run:
        typer.echo(f"Seeded tool: {entry.slug} (created)")
    elif deduped_from_slug and not dry_run:
        typer.echo(f"Seeded tool: {tool.slug} (deduped from {deduped_from_slug})")
    elif not dry_run:
        typer.echo(f"Seeded tool: {entry.slug} (updated)")
