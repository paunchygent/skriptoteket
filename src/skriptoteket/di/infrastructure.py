"""Infrastructure provider: database, repositories, core services."""

from __future__ import annotations

from collections.abc import AsyncIterator

from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
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
from skriptoteket.infrastructure.repositories.script_suggestion_decision_repository import (
    PostgreSQLScriptSuggestionDecisionRepository,
)
from skriptoteket.infrastructure.repositories.script_suggestion_repository import (
    PostgreSQLScriptSuggestionRepository,
)
from skriptoteket.infrastructure.repositories.session_repository import PostgreSQLSessionRepository
from skriptoteket.infrastructure.repositories.tool_maintainer_audit_repository import (
    PostgreSQLToolMaintainerAuditRepository,
)
from skriptoteket.infrastructure.repositories.tool_maintainer_repository import (
    PostgreSQLToolMaintainerRepository,
)
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
    ProfessionRepositoryProtocol,
    ToolMaintainerAuditRepositoryProtocol,
    ToolMaintainerRepositoryProtocol,
    ToolRepositoryProtocol,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.identity import (
    PasswordHasherProtocol,
    SessionRepositoryProtocol,
    UserRepositoryProtocol,
)
from skriptoteket.protocols.runner import ArtifactManagerProtocol, ToolRunnerProtocol
from skriptoteket.protocols.scripting import (
    ToolRunRepositoryProtocol,
    ToolVersionRepositoryProtocol,
)
from skriptoteket.protocols.suggestions import (
    SuggestionDecisionRepositoryProtocol,
    SuggestionRepositoryProtocol,
)
from skriptoteket.protocols.token_generator import TokenGeneratorProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class InfrastructureProvider(Provider):
    """Provides database, repositories, and core infrastructure services."""

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
            try:
                yield session
            finally:
                if session.in_transaction():
                    await session.rollback()

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

    # Repositories

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
    def tool_maintainer_repo(self, session: AsyncSession) -> ToolMaintainerRepositoryProtocol:
        return PostgreSQLToolMaintainerRepository(session)

    @provide(scope=Scope.REQUEST)
    def tool_maintainer_audit_repo(
        self, session: AsyncSession
    ) -> ToolMaintainerAuditRepositoryProtocol:
        return PostgreSQLToolMaintainerAuditRepository(session)

    @provide(scope=Scope.REQUEST)
    def tool_version_repo(self, session: AsyncSession) -> ToolVersionRepositoryProtocol:
        return PostgreSQLToolVersionRepository(session)

    @provide(scope=Scope.REQUEST)
    def tool_run_repo(self, session: AsyncSession) -> ToolRunRepositoryProtocol:
        return PostgreSQLToolRunRepository(session)

    @provide(scope=Scope.REQUEST)
    def script_suggestion_repo(self, session: AsyncSession) -> SuggestionRepositoryProtocol:
        return PostgreSQLScriptSuggestionRepository(session)

    @provide(scope=Scope.REQUEST)
    def script_suggestion_decision_repo(
        self, session: AsyncSession
    ) -> SuggestionDecisionRepositoryProtocol:
        return PostgreSQLScriptSuggestionDecisionRepository(session)
