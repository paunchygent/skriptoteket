from __future__ import annotations

import asyncio

import typer

from skriptoteket.application.identity.commands import CreateLocalUserCommand
from skriptoteket.application.identity.handlers.create_local_user import CreateLocalUserHandler
from skriptoteket.cli._db import open_session
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role
from skriptoteket.infrastructure.clock import UTCClock
from skriptoteket.infrastructure.db.uow import SQLAlchemyUnitOfWork
from skriptoteket.infrastructure.id_generator import UUID4Generator
from skriptoteket.infrastructure.repositories.profile_repository import PostgreSQLProfileRepository
from skriptoteket.infrastructure.repositories.user_repository import PostgreSQLUserRepository
from skriptoteket.infrastructure.security.password_hasher import Argon2PasswordHasher


def bootstrap_superuser(
    email: str = typer.Option(..., prompt=True),
    password: str = typer.Option(..., prompt=True, hide_input=True, confirmation_prompt=True),
) -> None:
    """Create the first superuser (admin-provisioned accounts; no self-signup)."""
    asyncio.run(_bootstrap_superuser_async(email=email, password=password))


async def _bootstrap_superuser_async(*, email: str, password: str) -> None:
    settings = Settings()
    async with open_session(settings) as session:
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
