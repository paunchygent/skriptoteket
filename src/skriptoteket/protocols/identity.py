"""Identity protocols for persistence and application-level domain services.

Purpose:
  Define the protocol-first seams used by handlers, repositories, and
  registration domain validation without binding the application layer to
  concrete infrastructure.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from skriptoteket.application.identity.admin_users import (
    GetUserQuery,
    GetUserResult,
    ListUsersQuery,
    ListUsersResult,
)
from skriptoteket.application.identity.commands import (
    ChangeEmailCommand,
    ChangeEmailResult,
    ChangePasswordCommand,
    CreateLocalUserCommand,
    CreateLocalUserResult,
    GetProfileCommand,
    GetProfileResult,
    LoginCommand,
    LoginResult,
    LogoutCommand,
    RegisterUserCommand,
    RegisterUserResult,
    UpdateAiSettingsCommand,
    UpdateAiSettingsResult,
    UpdateProfileCommand,
    UpdateProfileResult,
    ValidateRegistrationCommand,
    ValidateRegistrationResult,
)
from skriptoteket.domain.identity.models import (
    AllowedDomain,
    BlockedDomain,
    Role,
    Session,
    User,
    UserAuth,
    UserProfile,
)


class UserRepositoryProtocol(Protocol):
    async def get_by_id(self, user_id: UUID) -> User | None: ...
    async def get_auth_by_email(self, email: str) -> UserAuth | None: ...
    async def create(self, *, user: User, password_hash: str | None) -> User: ...
    async def update(self, *, user: User) -> User: ...
    async def update_password_hash(
        self, *, user_id: UUID, password_hash: str, updated_at: datetime
    ) -> None: ...
    async def list_users(self, *, limit: int, offset: int) -> list[User]: ...
    async def count_all(self) -> int: ...
    async def count_active_by_role(self) -> dict[Role, int]: ...


class ProfileRepositoryProtocol(Protocol):
    async def get_by_user_id(self, *, user_id: UUID) -> UserProfile | None: ...
    async def create(self, *, profile: UserProfile) -> UserProfile: ...
    async def update(self, *, profile: UserProfile) -> UserProfile: ...


class SessionRepositoryProtocol(Protocol):
    async def create(self, *, session: Session) -> None: ...
    async def get_by_id(self, session_id: UUID) -> Session | None: ...
    async def revoke(self, *, session_id: UUID) -> None: ...
    async def revoke_all_for_user(self, *, user_id: UUID, revoked_at: datetime) -> int: ...
    async def count_active(self, *, now: datetime) -> int: ...
    async def sync_ai_settings_for_user(
        self,
        *,
        user_id: UUID,
        allow_remote_fallback: bool | None,
        inline_completion_provider: str | None,
        now: datetime,
    ) -> None: ...


class AllowedDomainRepositoryProtocol(Protocol):
    async def get_by_domain(self, domain: str) -> AllowedDomain | None: ...
    async def upsert(self, *, domain: AllowedDomain) -> AllowedDomain: ...
    async def list_all(self) -> list[AllowedDomain]: ...


class BlockedDomainRepositoryProtocol(Protocol):
    async def get_by_domain(self, domain: str) -> BlockedDomain | None: ...
    async def upsert(self, *, domain: BlockedDomain) -> BlockedDomain: ...
    async def list_all(self) -> list[BlockedDomain]: ...


class DomainValidatorProtocol(Protocol):
    def normalize_seed_domain(self, domain: str) -> str: ...
    def extract_root_domain_from_email(self, email: str) -> str: ...
    async def validate_registration_email(self, email: str) -> None: ...


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


class ProvisionLocalUserHandlerProtocol(Protocol):
    async def handle(
        self, *, actor: User, command: CreateLocalUserCommand
    ) -> CreateLocalUserResult: ...


class RegisterUserHandlerProtocol(Protocol):
    async def handle(self, command: RegisterUserCommand) -> RegisterUserResult: ...


class ValidateRegistrationHandlerProtocol(Protocol):
    async def handle(self, command: ValidateRegistrationCommand) -> ValidateRegistrationResult: ...


class GetProfileHandlerProtocol(Protocol):
    async def handle(self, command: GetProfileCommand) -> GetProfileResult: ...


class UpdateProfileHandlerProtocol(Protocol):
    async def handle(self, command: UpdateProfileCommand) -> UpdateProfileResult: ...


class UpdateAiSettingsHandlerProtocol(Protocol):
    async def handle(self, command: UpdateAiSettingsCommand) -> UpdateAiSettingsResult: ...


class ChangePasswordHandlerProtocol(Protocol):
    async def handle(self, command: ChangePasswordCommand) -> None: ...


class ChangeEmailHandlerProtocol(Protocol):
    async def handle(self, command: ChangeEmailCommand) -> ChangeEmailResult: ...


class ListUsersHandlerProtocol(Protocol):
    async def handle(self, *, actor: User, query: ListUsersQuery) -> ListUsersResult: ...


class GetUserHandlerProtocol(Protocol):
    async def handle(self, *, actor: User, query: GetUserQuery) -> GetUserResult: ...
