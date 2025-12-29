"""Editor domain provider: draft workflows, locks, sandbox, and review actions."""

from __future__ import annotations

from dishka import Provider, Scope, provide

from skriptoteket.application.scripting.handlers.acquire_draft_lock import (
    AcquireDraftLockHandler,
)
from skriptoteket.application.scripting.handlers.create_draft_version import (
    CreateDraftVersionHandler,
)
from skriptoteket.application.scripting.handlers.publish_version import PublishVersionHandler
from skriptoteket.application.scripting.handlers.release_draft_lock import (
    ReleaseDraftLockHandler,
)
from skriptoteket.application.scripting.handlers.request_changes import RequestChangesHandler
from skriptoteket.application.scripting.handlers.resolve_sandbox_settings import (
    ResolveSandboxSettingsHandler,
)
from skriptoteket.application.scripting.handlers.rollback_version import RollbackVersionHandler
from skriptoteket.application.scripting.handlers.run_sandbox import RunSandboxHandler
from skriptoteket.application.scripting.handlers.save_draft_version import SaveDraftVersionHandler
from skriptoteket.application.scripting.handlers.save_sandbox_settings import (
    SaveSandboxSettingsHandler,
)
from skriptoteket.application.scripting.handlers.start_sandbox_action import (
    StartSandboxActionHandler,
)
from skriptoteket.application.scripting.handlers.submit_for_review import SubmitForReviewHandler
from skriptoteket.application.scripting.tool_settings_service import ToolSettingsService
from skriptoteket.config import Settings
from skriptoteket.protocols.catalog import (
    ToolMaintainerRepositoryProtocol,
    ToolRepositoryProtocol,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.draft_locks import (
    AcquireDraftLockHandlerProtocol,
    DraftLockRepositoryProtocol,
    ReleaseDraftLockHandlerProtocol,
)
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.sandbox_snapshots import SandboxSnapshotRepositoryProtocol
from skriptoteket.protocols.scripting import (
    CreateDraftVersionHandlerProtocol,
    ExecuteToolVersionHandlerProtocol,
    PublishVersionHandlerProtocol,
    RequestChangesHandlerProtocol,
    RollbackVersionHandlerProtocol,
    RunSandboxHandlerProtocol,
    SaveDraftVersionHandlerProtocol,
    StartSandboxActionHandlerProtocol,
    SubmitForReviewHandlerProtocol,
    ToolVersionRepositoryProtocol,
)
from skriptoteket.protocols.session_files import SessionFileStorageProtocol
from skriptoteket.protocols.tool_sessions import ToolSessionRepositoryProtocol
from skriptoteket.protocols.tool_settings import (
    ResolveSandboxSettingsHandlerProtocol,
    SaveSandboxSettingsHandlerProtocol,
    ToolSettingsServiceProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class EditorProvider(Provider):
    """Provides editor-specific draft/sandbox handlers."""

    @provide(scope=Scope.REQUEST)
    def create_draft_version_handler(
        self,
        uow: UnitOfWorkProtocol,
        tools: ToolRepositoryProtocol,
        maintainers: ToolMaintainerRepositoryProtocol,
        versions: ToolVersionRepositoryProtocol,
        locks: DraftLockRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> CreateDraftVersionHandlerProtocol:
        return CreateDraftVersionHandler(
            uow=uow,
            tools=tools,
            maintainers=maintainers,
            versions=versions,
            locks=locks,
            clock=clock,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def save_draft_version_handler(
        self,
        settings: Settings,
        uow: UnitOfWorkProtocol,
        versions: ToolVersionRepositoryProtocol,
        maintainers: ToolMaintainerRepositoryProtocol,
        locks: DraftLockRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> SaveDraftVersionHandlerProtocol:
        return SaveDraftVersionHandler(
            settings=settings,
            uow=uow,
            versions=versions,
            maintainers=maintainers,
            locks=locks,
            clock=clock,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def acquire_draft_lock_handler(
        self,
        settings: Settings,
        uow: UnitOfWorkProtocol,
        locks: DraftLockRepositoryProtocol,
        clock: ClockProtocol,
    ) -> AcquireDraftLockHandlerProtocol:
        return AcquireDraftLockHandler(
            settings=settings,
            uow=uow,
            locks=locks,
            clock=clock,
        )

    @provide(scope=Scope.REQUEST)
    def release_draft_lock_handler(
        self,
        uow: UnitOfWorkProtocol,
        locks: DraftLockRepositoryProtocol,
    ) -> ReleaseDraftLockHandlerProtocol:
        return ReleaseDraftLockHandler(
            uow=uow,
            locks=locks,
        )

    @provide(scope=Scope.REQUEST)
    def submit_for_review_handler(
        self,
        uow: UnitOfWorkProtocol,
        versions: ToolVersionRepositoryProtocol,
        maintainers: ToolMaintainerRepositoryProtocol,
        clock: ClockProtocol,
    ) -> SubmitForReviewHandlerProtocol:
        return SubmitForReviewHandler(
            uow=uow,
            versions=versions,
            maintainers=maintainers,
            clock=clock,
        )

    @provide(scope=Scope.REQUEST)
    def publish_version_handler(
        self,
        uow: UnitOfWorkProtocol,
        tools: ToolRepositoryProtocol,
        versions: ToolVersionRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> PublishVersionHandlerProtocol:
        return PublishVersionHandler(
            uow=uow,
            tools=tools,
            versions=versions,
            clock=clock,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def rollback_version_handler(
        self,
        uow: UnitOfWorkProtocol,
        tools: ToolRepositoryProtocol,
        versions: ToolVersionRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> RollbackVersionHandlerProtocol:
        return RollbackVersionHandler(
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
        settings: Settings,
        versions: ToolVersionRepositoryProtocol,
        maintainers: ToolMaintainerRepositoryProtocol,
        locks: DraftLockRepositoryProtocol,
        clock: ClockProtocol,
        sessions: ToolSessionRepositoryProtocol,
        id_generator: IdGeneratorProtocol,
        execute: ExecuteToolVersionHandlerProtocol,
        session_files: SessionFileStorageProtocol,
        snapshots: SandboxSnapshotRepositoryProtocol,
    ) -> RunSandboxHandlerProtocol:
        return RunSandboxHandler(
            uow=uow,
            settings=settings,
            versions=versions,
            maintainers=maintainers,
            locks=locks,
            clock=clock,
            sessions=sessions,
            id_generator=id_generator,
            execute=execute,
            session_files=session_files,
            snapshots=snapshots,
        )

    @provide(scope=Scope.REQUEST)
    def start_sandbox_action_handler(
        self,
        uow: UnitOfWorkProtocol,
        versions: ToolVersionRepositoryProtocol,
        maintainers: ToolMaintainerRepositoryProtocol,
        locks: DraftLockRepositoryProtocol,
        clock: ClockProtocol,
        sessions: ToolSessionRepositoryProtocol,
        execute: ExecuteToolVersionHandlerProtocol,
        session_files: SessionFileStorageProtocol,
        snapshots: SandboxSnapshotRepositoryProtocol,
    ) -> StartSandboxActionHandlerProtocol:
        return StartSandboxActionHandler(
            uow=uow,
            versions=versions,
            maintainers=maintainers,
            locks=locks,
            clock=clock,
            sessions=sessions,
            execute=execute,
            session_files=session_files,
            snapshots=snapshots,
        )

    @provide(scope=Scope.REQUEST)
    def tool_settings_service(
        self,
        sessions: ToolSessionRepositoryProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> ToolSettingsServiceProtocol:
        return ToolSettingsService(
            sessions=sessions,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def resolve_sandbox_settings_handler(
        self,
        uow: UnitOfWorkProtocol,
        versions: ToolVersionRepositoryProtocol,
        maintainers: ToolMaintainerRepositoryProtocol,
        locks: DraftLockRepositoryProtocol,
        clock: ClockProtocol,
        settings_service: ToolSettingsServiceProtocol,
    ) -> ResolveSandboxSettingsHandlerProtocol:
        return ResolveSandboxSettingsHandler(
            uow=uow,
            versions=versions,
            maintainers=maintainers,
            locks=locks,
            clock=clock,
            settings_service=settings_service,
        )

    @provide(scope=Scope.REQUEST)
    def save_sandbox_settings_handler(
        self,
        uow: UnitOfWorkProtocol,
        versions: ToolVersionRepositoryProtocol,
        maintainers: ToolMaintainerRepositoryProtocol,
        locks: DraftLockRepositoryProtocol,
        clock: ClockProtocol,
        settings_service: ToolSettingsServiceProtocol,
    ) -> SaveSandboxSettingsHandlerProtocol:
        return SaveSandboxSettingsHandler(
            uow=uow,
            versions=versions,
            maintainers=maintainers,
            locks=locks,
            clock=clock,
            settings_service=settings_service,
        )
