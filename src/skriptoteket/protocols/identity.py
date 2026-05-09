"""Identity protocols for persistence and application-level domain services.

Purpose:
  Define the protocol-first seams used by handlers, repositories, and
  registration domain validation without binding the application layer to
  concrete infrastructure.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import TYPE_CHECKING, Protocol
from uuid import UUID

from skriptoteket.application.identity.admin_users import (
    DeactivateUserCommand,
    DeactivateUserResult,
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
    RegisterUserCommand,
    RegisterUserResult,
    UpdateAiSettingsCommand,
    UpdateAiSettingsResult,
    UpdateClassroomPlannerSettingsCommand,
    UpdateClassroomPlannerSettingsResult,
    UpdateProfileCommand,
    UpdateProfileResult,
    ValidateRegistrationCommand,
    ValidateRegistrationResult,
)
from skriptoteket.domain.identity.models import (
    AllowedDomain,
    BlockedDomain,
    Role,
    User,
    UserAuth,
    UserProfile,
)
from skriptoteket.domain.identity.projections import IdentityProjection, IdentityProjectionEvent

if TYPE_CHECKING:
    from skriptoteket.application.identity.huleedu_app_projection import HuleEduAppUserProjection
    from skriptoteket.domain.identity.internal_identity_context import InternalIdentityContextV1


class UserRepositoryProtocol(Protocol):
    async def get_by_id(self, user_id: UUID) -> User | None: ...
    async def get_auth_by_email(self, email: str) -> UserAuth | None: ...
    async def create(self, *, user: User, password_hash: str | None) -> User: ...
    async def create_if_email_available(
        self, *, user: User, password_hash: str | None
    ) -> User | None: ...
    async def update(self, *, user: User) -> User: ...
    async def update_password_hash(
        self, *, user_id: UUID, password_hash: str, updated_at: datetime
    ) -> None: ...
    async def list_users(self, *, limit: int, offset: int) -> list[User]: ...
    async def count_all(self) -> int: ...
    async def count_active_by_role(self) -> dict[Role, int]: ...


class UserLifecycleRepositoryProtocol(Protocol):
    async def get_by_id(self, user_id: UUID) -> User | None: ...
    async def update(self, *, user: User) -> User: ...
    async def count_active_by_role(self) -> dict[Role, int]: ...


class ProfileRepositoryProtocol(Protocol):
    async def get_by_user_id(self, *, user_id: UUID) -> UserProfile | None: ...
    async def create(self, *, profile: UserProfile) -> UserProfile: ...
    async def update(self, *, profile: UserProfile) -> UserProfile: ...


class IdentityProjectionRepositoryProtocol(Protocol):
    async def lock_realm_subject(
        self,
        *,
        product_identity_realm: str,
        realm_subject_id: str,
    ) -> None: ...
    async def lock_email(self, *, email: str) -> None: ...
    async def get_by_realm_subject(
        self,
        *,
        product_identity_realm: str,
        realm_subject_id: str,
    ) -> IdentityProjection | None: ...
    async def create(self, *, projection: IdentityProjection) -> IdentityProjection: ...
    async def create_if_realm_subject_absent(
        self, *, projection: IdentityProjection
    ) -> IdentityProjection | None: ...


class IdentityProjectionEventRepositoryProtocol(Protocol):
    async def create(self, *, event: IdentityProjectionEvent) -> IdentityProjectionEvent: ...


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


class HuleEduInternalIdentityVerifierProtocol(Protocol):
    def verify(
        self,
        *,
        headers: Mapping[str, object],
        now_ts: int,
    ) -> InternalIdentityContextV1: ...


class HuleEduAppProjectionResolverProtocol(Protocol):
    async def resolve(
        self,
        *,
        context: InternalIdentityContextV1,
        correlation_id: UUID | None = None,
    ) -> HuleEduAppUserProjection: ...


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


class UpdateClassroomPlannerSettingsHandlerProtocol(Protocol):
    async def handle(
        self,
        command: UpdateClassroomPlannerSettingsCommand,
    ) -> UpdateClassroomPlannerSettingsResult: ...


class ChangePasswordHandlerProtocol(Protocol):
    async def handle(self, command: ChangePasswordCommand) -> None: ...


class ChangeEmailHandlerProtocol(Protocol):
    async def handle(self, command: ChangeEmailCommand) -> ChangeEmailResult: ...


class ListUsersHandlerProtocol(Protocol):
    async def handle(self, *, actor: User, query: ListUsersQuery) -> ListUsersResult: ...


class GetUserHandlerProtocol(Protocol):
    async def handle(self, *, actor: User, query: GetUserQuery) -> GetUserResult: ...


class DeactivateUserHandlerProtocol(Protocol):
    async def handle(
        self,
        *,
        actor: User,
        command: DeactivateUserCommand,
    ) -> DeactivateUserResult: ...
