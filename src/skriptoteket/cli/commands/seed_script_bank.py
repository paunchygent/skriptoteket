from __future__ import annotations

import asyncio
from enum import StrEnum

import typer

from skriptoteket.application.catalog.handlers.publish_tool import PublishToolHandler
from skriptoteket.application.catalog.handlers.update_tool_metadata import UpdateToolMetadataHandler
from skriptoteket.application.identity.authentication import authenticate_local_user
from skriptoteket.application.scripting.handlers.acquire_draft_lock import (
    AcquireDraftLockHandler,
)
from skriptoteket.application.scripting.handlers.create_draft_version import (
    CreateDraftVersionHandler,
)
from skriptoteket.application.scripting.handlers.publish_version import PublishVersionHandler
from skriptoteket.application.scripting.handlers.submit_for_review import SubmitForReviewHandler
from skriptoteket.cli._db import open_session
from skriptoteket.cli.commands.seed_script_bank_entry import seed_one_entry
from skriptoteket.config import Settings
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
from skriptoteket.script_bank.models import ScriptBankSeedGroup


class SeedProfile(StrEnum):
    DEV = "dev"
    PROD = "prod"


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
    profile: SeedProfile = typer.Option(
        SeedProfile.DEV,
        help="Seed profile: dev (curated + test) or prod (curated only).",
    ),
    group: list[ScriptBankSeedGroup] = typer.Option(
        [],
        "--group",
        help="Seed only these script-bank groups (repeatable). Overrides --profile.",
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
            pdm run python -m skriptoteket.cli seed-script-bank --dry-run --profile prod
    """
    asyncio.run(
        _seed_script_bank_async(
            actor_email=actor_email,
            actor_password=actor_password,
            slugs=slug,
            profile=profile,
            groups=group,
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
    profile: SeedProfile,
    groups: list[ScriptBankSeedGroup],
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
        acquire_draft_lock = AcquireDraftLockHandler(
            settings=settings,
            uow=uow,
            locks=locks,
            clock=clock,
        )
        submit_for_review = SubmitForReviewHandler(
            uow=uow,
            tools=tools,
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
        if groups:
            allowed_groups = set(groups)
        elif profile is SeedProfile.PROD:
            allowed_groups = {ScriptBankSeedGroup.CURATED}
        else:
            allowed_groups = {ScriptBankSeedGroup.CURATED, ScriptBankSeedGroup.TEST}

        selected_entries = [entry for entry in SCRIPT_BANK if entry.seed_group in allowed_groups]
        if slugs:
            selected_entries = [entry for entry in selected_entries if entry.slug in slug_set]
        if slugs and not selected_entries:
            raise SystemExit(f"No script-bank entries found for slugs: {', '.join(slugs)}")
        if not selected_entries:
            raise SystemExit("No script-bank entries found for the selected profile/groups.")

        for entry in selected_entries:
            await seed_one_entry(
                actor=actor,
                entry=entry,
                uow=uow,
                tools=tools,
                versions=versions,
                professions=professions,
                categories=categories,
                create_draft_version=create_draft_version,
                acquire_draft_lock=acquire_draft_lock,
                submit_for_review=submit_for_review,
                publish_version=publish_version,
                publish_tool=publish_tool_handler,
                update_tool_metadata_handler=update_tool_metadata_handler,
                sync_metadata=sync_metadata,
                sync_code=sync_code,
                publish=publish,
                dry_run=dry_run,
            )
