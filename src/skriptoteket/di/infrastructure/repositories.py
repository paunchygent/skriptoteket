"""Infrastructure provider: database-backed repositories."""

from __future__ import annotations

from dishka import Provider, Scope, provide
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.infrastructure.repositories.allowed_domain_repository import (
    PostgreSQLAllowedDomainRepository,
)
from skriptoteket.infrastructure.repositories.blocked_domain_repository import (
    PostgreSQLBlockedDomainRepository,
)
from skriptoteket.infrastructure.repositories.category_repository import (
    PostgreSQLCategoryRepository,
)
from skriptoteket.infrastructure.repositories.draft_lock_repository import (
    PostgreSQLDraftLockRepository,
)
from skriptoteket.infrastructure.repositories.email_verification_token_repository import (
    PostgreSQLEmailVerificationTokenRepository,
)
from skriptoteket.infrastructure.repositories.identity_projection_repository import (
    PostgreSQLIdentityProjectionEventRepository,
    PostgreSQLIdentityProjectionRepository,
)
from skriptoteket.infrastructure.repositories.login_event_repository import (
    PostgreSQLLoginEventRepository,
)
from skriptoteket.infrastructure.repositories.password_reset_token_repository import (
    PostgreSQLPasswordResetTokenRepository,
)
from skriptoteket.infrastructure.repositories.profession_repository import (
    PostgreSQLProfessionRepository,
)
from skriptoteket.infrastructure.repositories.profile_repository import (
    PostgreSQLProfileRepository,
)
from skriptoteket.infrastructure.repositories.sandbox_snapshot_repository import (
    PostgreSQLSandboxSnapshotRepository,
)
from skriptoteket.infrastructure.repositories.script_suggestion_decision_repository import (
    PostgreSQLScriptSuggestionDecisionRepository,
)
from skriptoteket.infrastructure.repositories.script_suggestion_repository import (
    PostgreSQLScriptSuggestionRepository,
)
from skriptoteket.infrastructure.repositories.tool_maintainer_audit_repository import (
    PostgreSQLToolMaintainerAuditRepository,
)
from skriptoteket.infrastructure.repositories.tool_maintainer_repository import (
    PostgreSQLToolMaintainerRepository,
)
from skriptoteket.infrastructure.repositories.tool_repository import PostgreSQLToolRepository
from skriptoteket.infrastructure.repositories.tool_run_job_repository import (
    PostgreSQLToolRunJobRepository,
)
from skriptoteket.infrastructure.repositories.tool_run_repository import PostgreSQLToolRunRepository
from skriptoteket.infrastructure.repositories.tool_session_message_repository import (
    PostgreSQLToolSessionMessageRepository,
)
from skriptoteket.infrastructure.repositories.tool_session_repository import (
    PostgreSQLToolSessionRepository,
)
from skriptoteket.infrastructure.repositories.tool_session_turn_repository import (
    PostgreSQLToolSessionTurnRepository,
)
from skriptoteket.infrastructure.repositories.tool_version_repository import (
    PostgreSQLToolVersionRepository,
)
from skriptoteket.infrastructure.repositories.user_favorite_repository import (
    PostgreSQLFavoritesRepository,
)
from skriptoteket.infrastructure.repositories.user_repository import PostgreSQLUserRepository
from skriptoteket.infrastructure.repositories.user_vault_file_repository import (
    PostgreSQLUserVaultFileRepository,
)
from skriptoteket.infrastructure.repositories.user_vault_usage_repository import (
    PostgreSQLUserVaultUsageRepository,
)
from skriptoteket.protocols.catalog import (
    CategoryRepositoryProtocol,
    ProfessionRepositoryProtocol,
    ToolMaintainerAuditRepositoryProtocol,
    ToolMaintainerRepositoryProtocol,
    ToolRepositoryProtocol,
)
from skriptoteket.protocols.draft_locks import DraftLockRepositoryProtocol
from skriptoteket.protocols.email_verification import EmailVerificationTokenRepositoryProtocol
from skriptoteket.protocols.execution_queue import ToolRunJobRepositoryProtocol
from skriptoteket.protocols.favorites import FavoritesRepositoryProtocol
from skriptoteket.protocols.identity import (
    AllowedDomainRepositoryProtocol,
    BlockedDomainRepositoryProtocol,
    IdentityProjectionEventRepositoryProtocol,
    IdentityProjectionRepositoryProtocol,
    ProfileRepositoryProtocol,
    UserRepositoryProtocol,
)
from skriptoteket.protocols.login_events import LoginEventRepositoryProtocol
from skriptoteket.protocols.password_reset import PasswordResetTokenRepositoryProtocol
from skriptoteket.protocols.sandbox_snapshots import SandboxSnapshotRepositoryProtocol
from skriptoteket.protocols.scripting import (
    ToolRunRepositoryProtocol,
    ToolVersionRepositoryProtocol,
)
from skriptoteket.protocols.suggestions import (
    SuggestionDecisionRepositoryProtocol,
    SuggestionRepositoryProtocol,
)
from skriptoteket.protocols.tool_session_messages import ToolSessionMessageRepositoryProtocol
from skriptoteket.protocols.tool_session_turns import ToolSessionTurnRepositoryProtocol
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from skriptoteket.protocols.vault import (
    VaultFileRepositoryProtocol,
    VaultUsageRepositoryProtocol,
)


class InfrastructureRepositoryProvider(Provider):
    """Provides database-backed repository bindings."""

    @provide(scope=Scope.REQUEST)
    def allowed_domain_repo(self, session: AsyncSession) -> AllowedDomainRepositoryProtocol:
        return PostgreSQLAllowedDomainRepository(session)

    @provide(scope=Scope.REQUEST)
    def blocked_domain_repo(self, session: AsyncSession) -> BlockedDomainRepositoryProtocol:
        return PostgreSQLBlockedDomainRepository(session)

    @provide(scope=Scope.REQUEST)
    def user_repo(self, session: AsyncSession) -> UserRepositoryProtocol:
        return PostgreSQLUserRepository(session)

    @provide(scope=Scope.REQUEST)
    def login_event_repo(self, session: AsyncSession) -> LoginEventRepositoryProtocol:
        return PostgreSQLLoginEventRepository(session)

    @provide(scope=Scope.REQUEST)
    def identity_projection_repo(
        self,
        session: AsyncSession,
    ) -> IdentityProjectionRepositoryProtocol:
        return PostgreSQLIdentityProjectionRepository(session)

    @provide(scope=Scope.REQUEST)
    def identity_projection_event_repo(
        self,
        session: AsyncSession,
    ) -> IdentityProjectionEventRepositoryProtocol:
        return PostgreSQLIdentityProjectionEventRepository(session)

    @provide(scope=Scope.REQUEST)
    def profile_repo(self, session: AsyncSession) -> ProfileRepositoryProtocol:
        return PostgreSQLProfileRepository(session)

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
    def favorites_repo(self, session: AsyncSession) -> FavoritesRepositoryProtocol:
        return PostgreSQLFavoritesRepository(session)

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
    def tool_run_job_repo(self, session: AsyncSession) -> ToolRunJobRepositoryProtocol:
        return PostgreSQLToolRunJobRepository(session)

    @provide(scope=Scope.REQUEST)
    def tool_session_repo(self, session: AsyncSession) -> ToolSessionRepositoryProtocol:
        return PostgreSQLToolSessionRepository(session)

    @provide(scope=Scope.REQUEST)
    def tool_session_message_repo(
        self, session: AsyncSession
    ) -> ToolSessionMessageRepositoryProtocol:
        return PostgreSQLToolSessionMessageRepository(session)

    @provide(scope=Scope.REQUEST)
    def tool_session_turn_repo(self, session: AsyncSession) -> ToolSessionTurnRepositoryProtocol:
        return PostgreSQLToolSessionTurnRepository(session)

    @provide(scope=Scope.REQUEST)
    def draft_lock_repo(self, session: AsyncSession) -> DraftLockRepositoryProtocol:
        return PostgreSQLDraftLockRepository(session)

    @provide(scope=Scope.REQUEST)
    def sandbox_snapshot_repo(self, session: AsyncSession) -> SandboxSnapshotRepositoryProtocol:
        return PostgreSQLSandboxSnapshotRepository(session)

    @provide(scope=Scope.REQUEST)
    def script_suggestion_repo(self, session: AsyncSession) -> SuggestionRepositoryProtocol:
        return PostgreSQLScriptSuggestionRepository(session)

    @provide(scope=Scope.REQUEST)
    def script_suggestion_decision_repo(
        self, session: AsyncSession
    ) -> SuggestionDecisionRepositoryProtocol:
        return PostgreSQLScriptSuggestionDecisionRepository(session)

    @provide(scope=Scope.REQUEST)
    def email_verification_token_repo(
        self, session: AsyncSession
    ) -> EmailVerificationTokenRepositoryProtocol:
        return PostgreSQLEmailVerificationTokenRepository(session)

    @provide(scope=Scope.REQUEST)
    def password_reset_token_repo(
        self, session: AsyncSession
    ) -> PasswordResetTokenRepositoryProtocol:
        return PostgreSQLPasswordResetTokenRepository(session)

    @provide(scope=Scope.REQUEST)
    def vault_file_repo(self, session: AsyncSession) -> VaultFileRepositoryProtocol:
        return PostgreSQLUserVaultFileRepository(session)

    @provide(scope=Scope.REQUEST)
    def vault_usage_repo(self, session: AsyncSession) -> VaultUsageRepositoryProtocol:
        return PostgreSQLUserVaultUsageRepository(session)
