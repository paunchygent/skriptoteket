from __future__ import annotations

import asyncio

import typer
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from skriptoteket.application.identity.authentication import authenticate_local_user
from skriptoteket.application.identity.commands import CreateLocalUserCommand
from skriptoteket.application.identity.handlers.create_local_user import CreateLocalUserHandler
from skriptoteket.application.identity.handlers.provision_local_user import (
    ProvisionLocalUserHandler,
)
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role
from skriptoteket.infrastructure.clock import UTCClock
from skriptoteket.infrastructure.db.uow import SQLAlchemyUnitOfWork
from skriptoteket.infrastructure.id_generator import UUID4Generator
from skriptoteket.infrastructure.repositories.user_repository import PostgreSQLUserRepository
from skriptoteket.infrastructure.security.password_hasher import Argon2PasswordHasher

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
            handler = CreateLocalUserHandler(
                settings=settings,
                uow=uow,
                users=users,
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
