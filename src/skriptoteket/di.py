from __future__ import annotations

from collections.abc import AsyncIterator

from dishka import Provider, Scope, make_async_container, provide
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from skriptoteket.application.catalog.handlers.depublish_tool import DepublishToolHandler
from skriptoteket.application.catalog.handlers.list_all_categories import ListAllCategoriesHandler
from skriptoteket.application.catalog.handlers.list_categories_for_profession import (
    ListCategoriesForProfessionHandler,
)
from skriptoteket.application.catalog.handlers.list_professions import ListProfessionsHandler
from skriptoteket.application.catalog.handlers.list_tools_by_tags import ListToolsByTagsHandler
from skriptoteket.application.catalog.handlers.list_tools_for_admin import ListToolsForAdminHandler
from skriptoteket.application.catalog.handlers.publish_tool import PublishToolHandler
from skriptoteket.application.catalog.handlers.update_tool_metadata import UpdateToolMetadataHandler
from skriptoteket.application.identity.current_user_provider import CurrentUserProvider
from skriptoteket.application.identity.handlers.create_local_user import CreateLocalUserHandler
from skriptoteket.application.identity.handlers.login import LoginHandler
from skriptoteket.application.identity.handlers.logout import LogoutHandler
from skriptoteket.application.identity.handlers.provision_local_user import (
    ProvisionLocalUserHandler,
)
from skriptoteket.application.scripting.handlers.create_draft_version import (
    CreateDraftVersionHandler,
)
from skriptoteket.application.scripting.handlers.execute_tool_version import (
    ExecuteToolVersionHandler,
)
from skriptoteket.application.scripting.handlers.run_active_tool import RunActiveToolHandler
from skriptoteket.application.scripting.handlers.run_sandbox import RunSandboxHandler
from skriptoteket.application.scripting.handlers.save_draft_version import SaveDraftVersionHandler
from skriptoteket.application.scripting.handlers.submit_for_review import SubmitForReviewHandler
from skriptoteket.application.suggestions.handlers.decide_suggestion import DecideSuggestionHandler
from skriptoteket.application.suggestions.handlers.get_suggestion_for_review import (
    GetSuggestionForReviewHandler,
)
from skriptoteket.application.suggestions.handlers.list_suggestions_for_review import (
    ListSuggestionsForReviewHandler,
)
from skriptoteket.application.suggestions.handlers.submit_suggestion import SubmitSuggestionHandler
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
from skriptoteket.infrastructure.repositories.script_suggestion_decision_repository import (
    PostgreSQLScriptSuggestionDecisionRepository,
)
from skriptoteket.infrastructure.repositories.script_suggestion_repository import (
    PostgreSQLScriptSuggestionRepository,
)
from skriptoteket.infrastructure.repositories.session_repository import PostgreSQLSessionRepository
from skriptoteket.infrastructure.repositories.tool_repository import PostgreSQLToolRepository
from skriptoteket.infrastructure.repositories.tool_run_repository import PostgreSQLToolRunRepository
from skriptoteket.infrastructure.repositories.tool_version_repository import (
    PostgreSQLToolVersionRepository,
)
from skriptoteket.infrastructure.repositories.user_repository import PostgreSQLUserRepository
from skriptoteket.infrastructure.runner.artifact_manager import FilesystemArtifactManager
from skriptoteket.infrastructure.runner.capacity import RunnerCapacityLimiter
from skriptoteket.infrastructure.runner.docker_runner import DockerRunnerLimits, DockerToolRunner
from skriptoteket.infrastructure.security.password_hasher import Argon2PasswordHasher
from skriptoteket.infrastructure.token_generator import SecureTokenGenerator
from skriptoteket.protocols.catalog import (
    CategoryRepositoryProtocol,
    DepublishToolHandlerProtocol,
    ListAllCategoriesHandlerProtocol,
    ListCategoriesForProfessionHandlerProtocol,
    ListProfessionsHandlerProtocol,
    ListToolsByTagsHandlerProtocol,
    ListToolsForAdminHandlerProtocol,
    ProfessionRepositoryProtocol,
    PublishToolHandlerProtocol,
    ToolRepositoryProtocol,
    UpdateToolMetadataHandlerProtocol,
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
from skriptoteket.protocols.runner import ArtifactManagerProtocol, ToolRunnerProtocol
from skriptoteket.protocols.scripting import (
    CreateDraftVersionHandlerProtocol,
    ExecuteToolVersionHandlerProtocol,
    PublishVersionHandlerProtocol,
    RequestChangesHandlerProtocol,
    RunActiveToolHandlerProtocol,
    RunSandboxHandlerProtocol,
    SaveDraftVersionHandlerProtocol,
    SubmitForReviewHandlerProtocol,
    ToolRunRepositoryProtocol,
    ToolVersionRepositoryProtocol,
)
from skriptoteket.protocols.suggestions import (
    DecideSuggestionHandlerProtocol,
    GetSuggestionForReviewHandlerProtocol,
    ListSuggestionsForReviewHandlerProtocol,
    SubmitSuggestionHandlerProtocol,
    SuggestionDecisionRepositoryProtocol,
    SuggestionRepositoryProtocol,
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

    @provide(scope=Scope.APP)
    def runner_capacity(self, settings: Settings) -> RunnerCapacityLimiter:
        return RunnerCapacityLimiter(max_concurrency=settings.RUNNER_MAX_CONCURRENCY)

    @provide(scope=Scope.APP)
    def artifact_manager(self, settings: Settings) -> ArtifactManagerProtocol:
        return FilesystemArtifactManager(artifacts_root=settings.ARTIFACTS_ROOT)

    @provide(scope=Scope.APP)
    def tool_runner(
        self,
        settings: Settings,
        capacity: RunnerCapacityLimiter,
        artifacts: ArtifactManagerProtocol,
    ) -> ToolRunnerProtocol:
        limits = DockerRunnerLimits(
            cpu_limit=settings.RUNNER_CPU_LIMIT,
            memory_limit=settings.RUNNER_MEMORY_LIMIT,
            pids_limit=settings.RUNNER_PIDS_LIMIT,
            tmpfs_tmp=settings.RUNNER_TMPFS_TMP,
        )
        return DockerToolRunner(
            runner_image=settings.RUNNER_IMAGE,
            sandbox_timeout_seconds=settings.RUNNER_TIMEOUT_SANDBOX_SECONDS,
            production_timeout_seconds=settings.RUNNER_TIMEOUT_PRODUCTION_SECONDS,
            limits=limits,
            output_max_stdout_bytes=settings.RUN_OUTPUT_MAX_STDOUT_BYTES,
            output_max_stderr_bytes=settings.RUN_OUTPUT_MAX_STDERR_BYTES,
            output_max_html_bytes=settings.RUN_OUTPUT_MAX_HTML_BYTES,
            output_max_error_summary_bytes=settings.RUN_OUTPUT_MAX_ERROR_SUMMARY_BYTES,
            capacity=capacity,
            artifacts=artifacts,
        )

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
    def tool_version_repo(self, session: AsyncSession) -> ToolVersionRepositoryProtocol:
        return PostgreSQLToolVersionRepository(session)

    @provide(scope=Scope.REQUEST)
    def tool_run_repo(self, session: AsyncSession) -> ToolRunRepositoryProtocol:
        return PostgreSQLToolRunRepository(session)

    @provide(scope=Scope.REQUEST)
    def execute_tool_version_handler(
        self,
        uow: UnitOfWorkProtocol,
        versions: ToolVersionRepositoryProtocol,
        runs: ToolRunRepositoryProtocol,
        runner: ToolRunnerProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> ExecuteToolVersionHandlerProtocol:
        return ExecuteToolVersionHandler(
            uow=uow,
            versions=versions,
            runs=runs,
            runner=runner,
            clock=clock,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def create_draft_version_handler(
        self,
        uow: UnitOfWorkProtocol,
        tools: ToolRepositoryProtocol,
        versions: ToolVersionRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> CreateDraftVersionHandlerProtocol:
        return CreateDraftVersionHandler(
            uow=uow,
            tools=tools,
            versions=versions,
            clock=clock,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def save_draft_version_handler(
        self,
        uow: UnitOfWorkProtocol,
        versions: ToolVersionRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> SaveDraftVersionHandlerProtocol:
        return SaveDraftVersionHandler(
            uow=uow,
            versions=versions,
            clock=clock,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def submit_for_review_handler(
        self,
        uow: UnitOfWorkProtocol,
        versions: ToolVersionRepositoryProtocol,
        clock: ClockProtocol,
    ) -> SubmitForReviewHandlerProtocol:
        return SubmitForReviewHandler(uow=uow, versions=versions, clock=clock)

    @provide(scope=Scope.REQUEST)
    def publish_version_handler(
        self,
        uow: UnitOfWorkProtocol,
        tools: ToolRepositoryProtocol,
        versions: ToolVersionRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> PublishVersionHandlerProtocol:
        from skriptoteket.application.scripting.handlers.publish_version import (
            PublishVersionHandler,
        )

        return PublishVersionHandler(
            uow=uow,
            tools=tools,
            versions=versions,
            clock=clock,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def request_changes_handler(
        self,
        uow: UnitOfWorkProtocol,
        versions: ToolVersionRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> RequestChangesHandlerProtocol:
        from skriptoteket.application.scripting.handlers.request_changes import (
            RequestChangesHandler,
        )

        return RequestChangesHandler(
            uow=uow,
            versions=versions,
            clock=clock,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def run_sandbox_handler(
        self,
        uow: UnitOfWorkProtocol,
        versions: ToolVersionRepositoryProtocol,
        execute: ExecuteToolVersionHandlerProtocol,
    ) -> RunSandboxHandlerProtocol:
        return RunSandboxHandler(uow=uow, versions=versions, execute=execute)

    @provide(scope=Scope.REQUEST)
    def run_active_tool_handler(
        self,
        uow: UnitOfWorkProtocol,
        tools: ToolRepositoryProtocol,
        versions: ToolVersionRepositoryProtocol,
        execute: ExecuteToolVersionHandlerProtocol,
    ) -> RunActiveToolHandlerProtocol:
        return RunActiveToolHandler(
            uow=uow,
            tools=tools,
            versions=versions,
            execute=execute,
        )

    @provide(scope=Scope.REQUEST)
    def script_suggestion_repo(self, session: AsyncSession) -> SuggestionRepositoryProtocol:
        return PostgreSQLScriptSuggestionRepository(session)

    @provide(scope=Scope.REQUEST)
    def script_suggestion_decision_repo(
        self, session: AsyncSession
    ) -> SuggestionDecisionRepositoryProtocol:
        return PostgreSQLScriptSuggestionDecisionRepository(session)

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
    def list_all_categories_handler(
        self, categories: CategoryRepositoryProtocol
    ) -> ListAllCategoriesHandlerProtocol:
        return ListAllCategoriesHandler(categories=categories)

    @provide(scope=Scope.REQUEST)
    def list_tools_by_tags_handler(
        self,
        professions: ProfessionRepositoryProtocol,
        categories: CategoryRepositoryProtocol,
        tools: ToolRepositoryProtocol,
    ) -> ListToolsByTagsHandlerProtocol:
        return ListToolsByTagsHandler(professions=professions, categories=categories, tools=tools)

    @provide(scope=Scope.REQUEST)
    def list_tools_for_admin_handler(
        self,
        tools: ToolRepositoryProtocol,
    ) -> ListToolsForAdminHandlerProtocol:
        return ListToolsForAdminHandler(tools=tools)

    @provide(scope=Scope.REQUEST)
    def publish_tool_handler(
        self,
        uow: UnitOfWorkProtocol,
        tools: ToolRepositoryProtocol,
        versions: ToolVersionRepositoryProtocol,
        clock: ClockProtocol,
    ) -> PublishToolHandlerProtocol:
        return PublishToolHandler(uow=uow, tools=tools, versions=versions, clock=clock)

    @provide(scope=Scope.REQUEST)
    def depublish_tool_handler(
        self,
        uow: UnitOfWorkProtocol,
        tools: ToolRepositoryProtocol,
        clock: ClockProtocol,
    ) -> DepublishToolHandlerProtocol:
        return DepublishToolHandler(uow=uow, tools=tools, clock=clock)

    @provide(scope=Scope.REQUEST)
    def update_tool_metadata_handler(
        self,
        uow: UnitOfWorkProtocol,
        tools: ToolRepositoryProtocol,
        clock: ClockProtocol,
    ) -> UpdateToolMetadataHandlerProtocol:
        return UpdateToolMetadataHandler(uow=uow, tools=tools, clock=clock)

    @provide(scope=Scope.REQUEST)
    def submit_suggestion_handler(
        self,
        uow: UnitOfWorkProtocol,
        suggestions: SuggestionRepositoryProtocol,
        professions: ProfessionRepositoryProtocol,
        categories: CategoryRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> SubmitSuggestionHandlerProtocol:
        return SubmitSuggestionHandler(
            uow=uow,
            suggestions=suggestions,
            professions=professions,
            categories=categories,
            clock=clock,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def list_suggestions_for_review_handler(
        self, suggestions: SuggestionRepositoryProtocol
    ) -> ListSuggestionsForReviewHandlerProtocol:
        return ListSuggestionsForReviewHandler(suggestions=suggestions)

    @provide(scope=Scope.REQUEST)
    def get_suggestion_for_review_handler(
        self,
        suggestions: SuggestionRepositoryProtocol,
        decisions: SuggestionDecisionRepositoryProtocol,
    ) -> GetSuggestionForReviewHandlerProtocol:
        return GetSuggestionForReviewHandler(suggestions=suggestions, decisions=decisions)

    @provide(scope=Scope.REQUEST)
    def decide_suggestion_handler(
        self,
        uow: UnitOfWorkProtocol,
        suggestions: SuggestionRepositoryProtocol,
        decisions: SuggestionDecisionRepositoryProtocol,
        tools: ToolRepositoryProtocol,
        professions: ProfessionRepositoryProtocol,
        categories: CategoryRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> DecideSuggestionHandlerProtocol:
        return DecideSuggestionHandler(
            uow=uow,
            suggestions=suggestions,
            decisions=decisions,
            tools=tools,
            professions=professions,
            categories=categories,
            clock=clock,
            id_generator=id_generator,
        )


def create_container(settings: Settings):
    return make_async_container(AppProvider(settings))
