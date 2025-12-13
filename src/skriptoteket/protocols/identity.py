from __future__ import annotations

from typing import Protocol
from uuid import UUID

from skriptoteket.application.identity.commands import (
    CreateLocalUserCommand,
    CreateLocalUserResult,
    LoginCommand,
    LoginResult,
    LogoutCommand,
)
from skriptoteket.domain.identity.models import Session, User, UserAuth


class UserRepositoryProtocol(Protocol):
    async def get_by_id(self, user_id: UUID) -> User | None: ...
    async def get_auth_by_email(self, email: str) -> UserAuth | None: ...
    async def create(self, *, user: User, password_hash: str | None) -> User: ...


class SessionRepositoryProtocol(Protocol):
    async def create(self, *, session: Session) -> None: ...
    async def get_by_id(self, session_id: UUID) -> Session | None: ...
    async def revoke(self, *, session_id: UUID) -> None: ...


class PasswordHasherProtocol(Protocol):
    def hash(self, *, password: str) -> str: ...
    def verify(self, *, password: str, password_hash: str) -> bool: ...


class CurrentUserProviderProtocol(Protocol):
    async def get_current_user(self, *, session_id: UUID | None) -> User | None: ...


class LoginHandlerProtocol(Protocol):
    async def handle(self, command: LoginCommand) -> LoginResult: ...


class LogoutHandlerProtocol(Protocol):
    async def handle(self, command: LogoutCommand) -> None: ...


class CreateLocalUserHandlerProtocol(Protocol):
    async def handle(self, command: CreateLocalUserCommand) -> CreateLocalUserResult: ...
