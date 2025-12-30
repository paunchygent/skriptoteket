"""Identity domain provider: authentication and user management handlers."""

from __future__ import annotations

from dishka import Provider, Scope, provide

from skriptoteket.application.identity.current_user_provider import CurrentUserProvider
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
from skriptoteket.application.identity.handlers.resend_verification import (
    ResendVerificationHandler,
    ResendVerificationHandlerProtocol,
)
from skriptoteket.application.identity.handlers.update_profile import UpdateProfileHandler
from skriptoteket.application.identity.handlers.verify_email import (
    VerifyEmailHandler,
    VerifyEmailHandlerProtocol,
)
from skriptoteket.config import Settings
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.email import EmailSenderProtocol, EmailTemplateRendererProtocol
from skriptoteket.protocols.email_verification import EmailVerificationTokenRepositoryProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.identity import (
    ChangeEmailHandlerProtocol,
    ChangePasswordHandlerProtocol,
    CreateLocalUserHandlerProtocol,
    CurrentUserProviderProtocol,
    GetProfileHandlerProtocol,
    GetUserHandlerProtocol,
    ListUsersHandlerProtocol,
    LoginHandlerProtocol,
    LogoutHandlerProtocol,
    PasswordHasherProtocol,
    ProfileRepositoryProtocol,
    ProvisionLocalUserHandlerProtocol,
    RegisterUserHandlerProtocol,
    SessionRepositoryProtocol,
    UpdateProfileHandlerProtocol,
    UserRepositoryProtocol,
)
from skriptoteket.protocols.login_events import (
    ListLoginEventsHandlerProtocol,
    LoginEventRepositoryProtocol,
)
from skriptoteket.protocols.token_generator import TokenGeneratorProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class IdentityProvider(Provider):
    """Provides identity/authentication handlers."""

    @provide(scope=Scope.REQUEST)
    def current_user_provider(
        self,
        users: UserRepositoryProtocol,
        sessions: SessionRepositoryProtocol,
        clock: ClockProtocol,
    ) -> CurrentUserProviderProtocol:
        return CurrentUserProvider(users=users, sessions=sessions, clock=clock)

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
        uow: UnitOfWorkProtocol,
        users: UserRepositoryProtocol,
        profiles: ProfileRepositoryProtocol,
        password_hasher: PasswordHasherProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> ProvisionLocalUserHandlerProtocol:
        return ProvisionLocalUserHandler(
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
        password_hasher: PasswordHasherProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
        token_generator: TokenGeneratorProtocol,
    ) -> RegisterUserHandlerProtocol:
        return RegisterUserHandler(
            settings=settings,
            uow=uow,
            users=users,
            profiles=profiles,
            verification_tokens=verification_tokens,
            email_sender=email_sender,
            email_renderer=email_renderer,
            password_hasher=password_hasher,
            clock=clock,
            id_generator=id_generator,
            token_generator=token_generator,
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
