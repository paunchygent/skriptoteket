"""Identity domain provider for app-local users and profiles.

Purpose:
    Bind Skriptoteket-owned user/profile handlers after browser session
    authority moved to HuleEdu.

Relationships:
    - Keeps admin/import provisioning and local role/profile management.
    - Does not bind retired browser login, logout, registration, or password
      lifecycle handlers.
"""

from __future__ import annotations

from dishka import Provider, Scope, provide

from skriptoteket.application.identity.domain_validator import TldextractDomainValidator
from skriptoteket.application.identity.handlers.create_local_user import CreateLocalUserHandler
from skriptoteket.application.identity.handlers.get_profile import GetProfileHandler
from skriptoteket.application.identity.handlers.get_user import GetUserHandler
from skriptoteket.application.identity.handlers.list_login_events import ListLoginEventsHandler
from skriptoteket.application.identity.handlers.list_users import ListUsersHandler
from skriptoteket.application.identity.handlers.provision_local_user import (
    ProvisionLocalUserHandler,
)
from skriptoteket.application.identity.handlers.update_ai_settings import UpdateAiSettingsHandler
from skriptoteket.application.identity.handlers.update_profile import UpdateProfileHandler
from skriptoteket.application.identity.huleedu_app_projection import (
    HuleEduAppProjectionResolver,
)
from skriptoteket.config import Settings
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.identity import (
    AllowedDomainRepositoryProtocol,
    BlockedDomainRepositoryProtocol,
    CreateLocalUserHandlerProtocol,
    DomainValidatorProtocol,
    GetProfileHandlerProtocol,
    GetUserHandlerProtocol,
    HuleEduAppProjectionResolverProtocol,
    IdentityProjectionEventRepositoryProtocol,
    IdentityProjectionRepositoryProtocol,
    ListUsersHandlerProtocol,
    PasswordHasherProtocol,
    ProfileRepositoryProtocol,
    ProvisionLocalUserHandlerProtocol,
    UpdateAiSettingsHandlerProtocol,
    UpdateProfileHandlerProtocol,
    UserRepositoryProtocol,
)
from skriptoteket.protocols.login_events import (
    ListLoginEventsHandlerProtocol,
    LoginEventRepositoryProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class IdentityProvider(Provider):
    """Provides identity/authentication handlers."""

    @provide(scope=Scope.REQUEST)
    def domain_validator(
        self,
        allowed_domains: AllowedDomainRepositoryProtocol,
        blocked_domains: BlockedDomainRepositoryProtocol,
    ) -> DomainValidatorProtocol:
        return TldextractDomainValidator(
            allowed_domains=allowed_domains,
            blocked_domains=blocked_domains,
        )

    @provide(scope=Scope.REQUEST)
    def huleedu_app_projection_resolver(
        self,
        uow: UnitOfWorkProtocol,
        users: UserRepositoryProtocol,
        profiles: ProfileRepositoryProtocol,
        projections: IdentityProjectionRepositoryProtocol,
        projection_events: IdentityProjectionEventRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> HuleEduAppProjectionResolverProtocol:
        return HuleEduAppProjectionResolver(
            uow=uow,
            users=users,
            profiles=profiles,
            projections=projections,
            projection_events=projection_events,
            clock=clock,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def create_local_user_handler(
        self,
        settings: Settings,
        uow: UnitOfWorkProtocol,
        users: UserRepositoryProtocol,
        profiles: ProfileRepositoryProtocol,
        password_hasher: PasswordHasherProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> CreateLocalUserHandlerProtocol:
        return CreateLocalUserHandler(
            settings=settings,
            uow=uow,
            users=users,
            profiles=profiles,
            password_hasher=password_hasher,
            clock=clock,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def provision_local_user_handler(
        self,
        settings: Settings,
        uow: UnitOfWorkProtocol,
        users: UserRepositoryProtocol,
        profiles: ProfileRepositoryProtocol,
        password_hasher: PasswordHasherProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> ProvisionLocalUserHandlerProtocol:
        return ProvisionLocalUserHandler(
            settings=settings,
            uow=uow,
            users=users,
            profiles=profiles,
            password_hasher=password_hasher,
            clock=clock,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def get_profile_handler(
        self,
        uow: UnitOfWorkProtocol,
        users: UserRepositoryProtocol,
        profiles: ProfileRepositoryProtocol,
    ) -> GetProfileHandlerProtocol:
        return GetProfileHandler(uow=uow, users=users, profiles=profiles)

    @provide(scope=Scope.REQUEST)
    def update_profile_handler(
        self,
        uow: UnitOfWorkProtocol,
        users: UserRepositoryProtocol,
        profiles: ProfileRepositoryProtocol,
        clock: ClockProtocol,
    ) -> UpdateProfileHandlerProtocol:
        return UpdateProfileHandler(uow=uow, users=users, profiles=profiles, clock=clock)

    @provide(scope=Scope.REQUEST)
    def update_ai_settings_handler(
        self,
        settings: Settings,
        uow: UnitOfWorkProtocol,
        users: UserRepositoryProtocol,
        profiles: ProfileRepositoryProtocol,
        clock: ClockProtocol,
    ) -> UpdateAiSettingsHandlerProtocol:
        return UpdateAiSettingsHandler(
            settings=settings,
            uow=uow,
            users=users,
            profiles=profiles,
            clock=clock,
        )

    @provide(scope=Scope.REQUEST)
    def list_users_handler(self, users: UserRepositoryProtocol) -> ListUsersHandlerProtocol:
        return ListUsersHandler(users=users)

    @provide(scope=Scope.REQUEST)
    def get_user_handler(self, users: UserRepositoryProtocol) -> GetUserHandlerProtocol:
        return GetUserHandler(users=users)

    @provide(scope=Scope.REQUEST)
    def list_login_events_handler(
        self,
        settings: Settings,
        clock: ClockProtocol,
        login_events: LoginEventRepositoryProtocol,
    ) -> ListLoginEventsHandlerProtocol:
        return ListLoginEventsHandler(
            settings=settings,
            clock=clock,
            login_events=login_events,
        )
