from __future__ import annotations

from collections.abc import AsyncIterator

from dishka import Provider, Scope, make_async_container, provide
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from skriptoteket.application.catalog.handlers.list_categories_for_profession import (
    ListCategoriesForProfessionHandler,
)
from skriptoteket.application.catalog.handlers.list_professions import ListProfessionsHandler
from skriptoteket.application.catalog.handlers.list_tools_by_tags import ListToolsByTagsHandler
from skriptoteket.application.identity.current_user_provider import CurrentUserProvider
from skriptoteket.application.identity.handlers.create_local_user import CreateLocalUserHandler
from skriptoteket.application.identity.handlers.login import LoginHandler
from skriptoteket.application.identity.handlers.logout import LogoutHandler
from skriptoteket.application.identity.handlers.provision_local_user import (
    ProvisionLocalUserHandler,
)
from skriptoteket.config import Settings
from skriptoteket.infrastructure.clock import UTCClock
from skriptoteket.infrastructure.db.uow import SQLAlchemyUnitOfWork
from skriptoteket.infrastructure.id_generator import UUID4Generator
from skriptoteket.infrastructure.repositories.category_repository import (
    PostgreSQLCategoryRepository,
)
from skriptoteket.infrastructure.repositories.profession_repository import (
    PostgreSQLProfessionRepository,
)
from skriptoteket.infrastructure.repositories.session_repository import PostgreSQLSessionRepository
from skriptoteket.infrastructure.repositories.tool_repository import PostgreSQLToolRepository
from skriptoteket.infrastructure.repositories.user_repository import PostgreSQLUserRepository
from skriptoteket.infrastructure.security.password_hasher import Argon2PasswordHasher
from skriptoteket.infrastructure.token_generator import SecureTokenGenerator
from skriptoteket.protocols.catalog import (
    CategoryRepositoryProtocol,
    ListCategoriesForProfessionHandlerProtocol,
    ListProfessionsHandlerProtocol,
    ListToolsByTagsHandlerProtocol,
    ProfessionRepositoryProtocol,
    ToolRepositoryProtocol,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.identity import (
    CreateLocalUserHandlerProtocol,
    CurrentUserProviderProtocol,
    LoginHandlerProtocol,
    LogoutHandlerProtocol,
    PasswordHasherProtocol,
    ProvisionLocalUserHandlerProtocol,
    SessionRepositoryProtocol,
    UserRepositoryProtocol,
)
from skriptoteket.protocols.token_generator import TokenGeneratorProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class AppProvider(Provider):
    def __init__(self, settings: Settings) -> None:
        super().__init__()
        self._settings = settings

    @provide(scope=Scope.APP)
    def settings(self) -> Settings:
        return self._settings

    @provide(scope=Scope.APP)
    def engine(self, settings: Settings) -> AsyncEngine:
        return create_async_engine(
            settings.DATABASE_URL,
            echo=settings.DATABASE_ECHO,
            pool_pre_ping=True,
        )

    @provide(scope=Scope.APP)
    def sessionmaker(self, engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
        return async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)

    @provide(scope=Scope.REQUEST)
    async def session(
        self,
        sessionmaker: async_sessionmaker[AsyncSession],
    ) -> AsyncIterator[AsyncSession]:
        async with sessionmaker() as session:
            yield session

    @provide(scope=Scope.REQUEST)
    def uow(self, session: AsyncSession) -> UnitOfWorkProtocol:
        return SQLAlchemyUnitOfWork(session)

    @provide(scope=Scope.APP)
    def clock(self) -> ClockProtocol:
        return UTCClock()

    @provide(scope=Scope.APP)
    def id_generator(self) -> IdGeneratorProtocol:
        return UUID4Generator()

    @provide(scope=Scope.APP)
    def token_generator(self) -> TokenGeneratorProtocol:
        return SecureTokenGenerator()

    @provide(scope=Scope.APP)
    def password_hasher(self) -> PasswordHasherProtocol:
        return Argon2PasswordHasher()

    @provide(scope=Scope.REQUEST)
    def user_repo(self, session: AsyncSession) -> UserRepositoryProtocol:
        return PostgreSQLUserRepository(session)

    @provide(scope=Scope.REQUEST)
    def session_repo(self, session: AsyncSession) -> SessionRepositoryProtocol:
        return PostgreSQLSessionRepository(session)

    @provide(scope=Scope.REQUEST)
    def profession_repo(self, session: AsyncSession) -> ProfessionRepositoryProtocol:
        return PostgreSQLProfessionRepository(session)

    @provide(scope=Scope.REQUEST)
    def category_repo(self, session: AsyncSession) -> CategoryRepositoryProtocol:
        return PostgreSQLCategoryRepository(session)

    @provide(scope=Scope.REQUEST)
    def tool_repo(self, session: AsyncSession) -> ToolRepositoryProtocol:
        return PostgreSQLToolRepository(session)

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
        sessions: SessionRepositoryProtocol,
        password_hasher: PasswordHasherProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
        token_generator: TokenGeneratorProtocol,
    ) -> LoginHandlerProtocol:
        return LoginHandler(
            settings=settings,
            uow=uow,
            users=users,
            sessions=sessions,
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
        password_hasher: PasswordHasherProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> CreateLocalUserHandlerProtocol:
        return CreateLocalUserHandler(
            settings=settings,
            uow=uow,
            users=users,
            password_hasher=password_hasher,
            clock=clock,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def provision_local_user_handler(
        self,
        uow: UnitOfWorkProtocol,
        users: UserRepositoryProtocol,
        password_hasher: PasswordHasherProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
        ) -> ProvisionLocalUserHandlerProtocol:
        return ProvisionLocalUserHandler(
            uow=uow,
            users=users,
            password_hasher=password_hasher,
            clock=clock,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def list_professions_handler(
        self, professions: ProfessionRepositoryProtocol
    ) -> ListProfessionsHandlerProtocol:
        return ListProfessionsHandler(professions=professions)

    @provide(scope=Scope.REQUEST)
    def list_categories_for_profession_handler(
        self,
        professions: ProfessionRepositoryProtocol,
        categories: CategoryRepositoryProtocol,
    ) -> ListCategoriesForProfessionHandlerProtocol:
        return ListCategoriesForProfessionHandler(professions=professions, categories=categories)

    @provide(scope=Scope.REQUEST)
    def list_tools_by_tags_handler(
        self,
        professions: ProfessionRepositoryProtocol,
        categories: CategoryRepositoryProtocol,
        tools: ToolRepositoryProtocol,
    ) -> ListToolsByTagsHandlerProtocol:
        return ListToolsByTagsHandler(professions=professions, categories=categories, tools=tools)


def create_container(settings: Settings):
    return make_async_container(AppProvider(settings))
