from __future__ import annotations

import asyncio
from importlib.resources import files as resource_files

import typer

from skriptoteket.application.catalog.commands import PublishToolCommand, UpdateToolMetadataCommand
from skriptoteket.application.catalog.handlers.publish_tool import PublishToolHandler
from skriptoteket.application.catalog.handlers.update_tool_metadata import UpdateToolMetadataHandler
from skriptoteket.application.identity.authentication import authenticate_local_user
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
from skriptoteket.cli._db import open_session
from skriptoteket.config import Settings
from skriptoteket.domain.catalog.models import Tool, update_tool_metadata
from skriptoteket.domain.identity.models import Role
from skriptoteket.infrastructure.clock import UTCClock
from skriptoteket.infrastructure.db.uow import SQLAlchemyUnitOfWork
from skriptoteket.infrastructure.id_generator import UUID4Generator
from skriptoteket.infrastructure.repositories.category_repository import (
    PostgreSQLCategoryRepository,
)
from skriptoteket.infrastructure.repositories.draft_lock_repository import (
    PostgreSQLDraftLockRepository,
)
from skriptoteket.infrastructure.repositories.profession_repository import (
    PostgreSQLProfessionRepository,
)
from skriptoteket.infrastructure.repositories.tool_maintainer_repository import (
    PostgreSQLToolMaintainerRepository,
)
from skriptoteket.infrastructure.repositories.tool_repository import PostgreSQLToolRepository
from skriptoteket.infrastructure.repositories.tool_version_repository import (
    PostgreSQLToolVersionRepository,
)
from skriptoteket.infrastructure.repositories.user_repository import PostgreSQLUserRepository
from skriptoteket.infrastructure.security.password_hasher import Argon2PasswordHasher
from skriptoteket.script_bank.bank import SCRIPT_BANK


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
    async with open_session(settings) as session:
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
        locks = PostgreSQLDraftLockRepository(session)

        create_draft_version = CreateDraftVersionHandler(
            uow=uow,
            tools=tools,
            maintainers=maintainers,
            versions=versions,
            locks=locks,
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
                    settings_schema=entry.settings_schema,
                    input_schema=entry.input_schema,
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
        or active_version.settings_schema != entry.settings_schema
        or active_version.input_schema != entry.input_schema
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
                    settings_schema=entry.settings_schema,
                    input_schema=entry.input_schema,
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
