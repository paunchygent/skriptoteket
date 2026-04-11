"""Identity domain provider: authentication and user management handlers."""

from __future__ import annotations

from dishka import Provider, Scope, provide

from skriptoteket.application.identity.current_user_provider import CurrentUserProvider
from skriptoteket.application.identity.domain_validator import TldextractDomainValidator
from skriptoteket.application.identity.handlers.change_email import ChangeEmailHandler
from skriptoteket.application.identity.handlers.change_password import ChangePasswordHandler
from skriptoteket.application.identity.handlers.create_local_user import CreateLocalUserHandler
from skriptoteket.application.identity.handlers.get_profile import GetProfileHandler
from skriptoteket.application.identity.handlers.get_user import GetUserHandler
from skriptoteket.application.identity.handlers.list_login_events import ListLoginEventsHandler
from skriptoteket.application.identity.handlers.list_users import ListUsersHandler
from skriptoteket.application.identity.handlers.login import LoginHandler
from skriptoteket.application.identity.handlers.logout import LogoutHandler
from skriptoteket.application.identity.handlers.provision_local_user import (
    ProvisionLocalUserHandler,
)
from skriptoteket.application.identity.handlers.register_user import RegisterUserHandler
from skriptoteket.application.identity.handlers.request_password_reset import (
    RequestPasswordResetHandler,
    RequestPasswordResetHandlerProtocol,
)
from skriptoteket.application.identity.handlers.resend_verification import (
    ResendVerificationHandler,
    ResendVerificationHandlerProtocol,
)
from skriptoteket.application.identity.handlers.reset_password import (
    ResetPasswordHandler,
    ResetPasswordHandlerProtocol,
)
from skriptoteket.application.identity.handlers.update_ai_settings import UpdateAiSettingsHandler
from skriptoteket.application.identity.handlers.update_profile import UpdateProfileHandler
from skriptoteket.application.identity.handlers.validate_registration_input import (
    ValidateRegistrationHandler,
)
from skriptoteket.application.identity.handlers.verify_email import (
    VerifyEmailHandler,
    VerifyEmailHandlerProtocol,
)
from skriptoteket.application.identity.huleedu_app_projection import (
    HuleEduAppProjectionResolver,
)
from skriptoteket.config import Settings
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.email import EmailSenderProtocol, EmailTemplateRendererProtocol
from skriptoteket.protocols.email_verification import EmailVerificationTokenRepositoryProtocol
from skriptoteket.protocols.favorites import FavoritesRepositoryProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.identity import (
    AllowedDomainRepositoryProtocol,
    BlockedDomainRepositoryProtocol,
    ChangeEmailHandlerProtocol,
    ChangePasswordHandlerProtocol,
    CreateLocalUserHandlerProtocol,
    CurrentUserProviderProtocol,
    DomainValidatorProtocol,
    GetProfileHandlerProtocol,
    GetUserHandlerProtocol,
    HuleEduAppProjectionResolverProtocol,
    ListUsersHandlerProtocol,
    LoginHandlerProtocol,
    LogoutHandlerProtocol,
    PasswordHasherProtocol,
    ProfileRepositoryProtocol,
    ProvisionLocalUserHandlerProtocol,
    RegisterUserHandlerProtocol,
    SessionRepositoryProtocol,
    UpdateAiSettingsHandlerProtocol,
    UpdateProfileHandlerProtocol,
    UserRepositoryProtocol,
    ValidateRegistrationHandlerProtocol,
)
from skriptoteket.protocols.login_events import (
    ListLoginEventsHandlerProtocol,
    LoginEventRepositoryProtocol,
)
from skriptoteket.protocols.password_reset import (
    PasswordResetRequestThrottleProtocol,
    PasswordResetTokenRepositoryProtocol,
)
from skriptoteket.protocols.sleeper import SleeperProtocol
from skriptoteket.protocols.token_generator import TokenGeneratorProtocol
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
    def current_user_provider(
        self,
        users: UserRepositoryProtocol,
        sessions: SessionRepositoryProtocol,
        clock: ClockProtocol,
    ) -> CurrentUserProviderProtocol:
        return CurrentUserProvider(users=users, sessions=sessions, clock=clock)

    @provide(scope=Scope.REQUEST)
    def huleedu_app_projection_resolver(
        self,
        uow: UnitOfWorkProtocol,
        users: UserRepositoryProtocol,
        profiles: ProfileRepositoryProtocol,
        clock: ClockProtocol,
    ) -> HuleEduAppProjectionResolverProtocol:
        return HuleEduAppProjectionResolver(
            uow=uow,
            users=users,
            profiles=profiles,
            clock=clock,
        )

    @provide(scope=Scope.REQUEST)
    def login_handler(
        self,
        settings: Settings,
        uow: UnitOfWorkProtocol,
        users: UserRepositoryProtocol,
        profiles: ProfileRepositoryProtocol,
        sessions: SessionRepositoryProtocol,
        login_events: LoginEventRepositoryProtocol,
        password_hasher: PasswordHasherProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
        token_generator: TokenGeneratorProtocol,
    ) -> LoginHandlerProtocol:
        return LoginHandler(
            settings=settings,
            uow=uow,
            users=users,
            profiles=profiles,
            sessions=sessions,
            login_events=login_events,
            password_hasher=password_hasher,
            clock=clock,
            id_generator=id_generator,
            token_generator=token_generator,
        )

    @provide(scope=Scope.REQUEST)
    def logout_handler(
        self,
        uow: UnitOfWorkProtocol,
        sessions: SessionRepositoryProtocol,
    ) -> LogoutHandlerProtocol:
        return LogoutHandler(uow=uow, sessions=sessions)

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
    def register_user_handler(
        self,
        settings: Settings,
        uow: UnitOfWorkProtocol,
        users: UserRepositoryProtocol,
        profiles: ProfileRepositoryProtocol,
        verification_tokens: EmailVerificationTokenRepositoryProtocol,
        email_sender: EmailSenderProtocol,
        email_renderer: EmailTemplateRendererProtocol,
        sleeper: SleeperProtocol,
        domain_validator: DomainValidatorProtocol,
        password_hasher: PasswordHasherProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
        token_generator: TokenGeneratorProtocol,
        favorites: FavoritesRepositoryProtocol,
        curated_apps: CuratedAppRegistryProtocol,
    ) -> RegisterUserHandlerProtocol:
        return RegisterUserHandler(
            settings=settings,
            uow=uow,
            users=users,
            profiles=profiles,
            verification_tokens=verification_tokens,
            email_sender=email_sender,
            email_renderer=email_renderer,
            sleeper=sleeper,
            domain_validator=domain_validator,
            password_hasher=password_hasher,
            clock=clock,
            id_generator=id_generator,
            token_generator=token_generator,
            favorites=favorites,
            curated_apps=curated_apps,
        )

    @provide(scope=Scope.REQUEST)
    def validate_registration_handler(
        self,
        users: UserRepositoryProtocol,
        domain_validator: DomainValidatorProtocol,
    ) -> ValidateRegistrationHandlerProtocol:
        return ValidateRegistrationHandler(users=users, domain_validator=domain_validator)

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
        sessions: SessionRepositoryProtocol,
        clock: ClockProtocol,
    ) -> UpdateAiSettingsHandlerProtocol:
        return UpdateAiSettingsHandler(
            settings=settings,
            uow=uow,
            users=users,
            profiles=profiles,
            sessions=sessions,
            clock=clock,
        )

    @provide(scope=Scope.REQUEST)
    def change_password_handler(
        self,
        uow: UnitOfWorkProtocol,
        users: UserRepositoryProtocol,
        password_hasher: PasswordHasherProtocol,
        clock: ClockProtocol,
    ) -> ChangePasswordHandlerProtocol:
        return ChangePasswordHandler(
            uow=uow,
            users=users,
            password_hasher=password_hasher,
            clock=clock,
        )

    @provide(scope=Scope.REQUEST)
    def change_email_handler(
        self,
        uow: UnitOfWorkProtocol,
        users: UserRepositoryProtocol,
        clock: ClockProtocol,
    ) -> ChangeEmailHandlerProtocol:
        return ChangeEmailHandler(uow=uow, users=users, clock=clock)

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

    @provide(scope=Scope.REQUEST)
    def verify_email_handler(
        self,
        uow: UnitOfWorkProtocol,
        users: UserRepositoryProtocol,
        verification_tokens: EmailVerificationTokenRepositoryProtocol,
        clock: ClockProtocol,
    ) -> VerifyEmailHandlerProtocol:
        return VerifyEmailHandler(
            uow=uow,
            users=users,
            verification_tokens=verification_tokens,
            clock=clock,
        )

    @provide(scope=Scope.REQUEST)
    def resend_verification_handler(
        self,
        settings: Settings,
        uow: UnitOfWorkProtocol,
        users: UserRepositoryProtocol,
        profiles: ProfileRepositoryProtocol,
        verification_tokens: EmailVerificationTokenRepositoryProtocol,
        email_sender: EmailSenderProtocol,
        email_renderer: EmailTemplateRendererProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
        token_generator: TokenGeneratorProtocol,
    ) -> ResendVerificationHandlerProtocol:
        return ResendVerificationHandler(
            settings=settings,
            uow=uow,
            users=users,
            profiles=profiles,
            verification_tokens=verification_tokens,
            email_sender=email_sender,
            email_renderer=email_renderer,
            clock=clock,
            id_generator=id_generator,
            token_generator=token_generator,
        )

    @provide(scope=Scope.REQUEST)
    def request_password_reset_handler(
        self,
        settings: Settings,
        uow: UnitOfWorkProtocol,
        users: UserRepositoryProtocol,
        profiles: ProfileRepositoryProtocol,
        password_reset_tokens: PasswordResetTokenRepositoryProtocol,
        password_reset_throttle: PasswordResetRequestThrottleProtocol,
        email_sender: EmailSenderProtocol,
        email_renderer: EmailTemplateRendererProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
        token_generator: TokenGeneratorProtocol,
    ) -> RequestPasswordResetHandlerProtocol:
        return RequestPasswordResetHandler(
            settings=settings,
            uow=uow,
            users=users,
            profiles=profiles,
            password_reset_tokens=password_reset_tokens,
            password_reset_throttle=password_reset_throttle,
            email_sender=email_sender,
            email_renderer=email_renderer,
            clock=clock,
            id_generator=id_generator,
            token_generator=token_generator,
        )

    @provide(scope=Scope.REQUEST)
    def reset_password_handler(
        self,
        uow: UnitOfWorkProtocol,
        users: UserRepositoryProtocol,
        sessions: SessionRepositoryProtocol,
        password_reset_tokens: PasswordResetTokenRepositoryProtocol,
        password_hasher: PasswordHasherProtocol,
        clock: ClockProtocol,
    ) -> ResetPasswordHandlerProtocol:
        return ResetPasswordHandler(
            uow=uow,
            users=users,
            sessions=sessions,
            password_reset_tokens=password_reset_tokens,
            password_hasher=password_hasher,
            clock=clock,
        )
