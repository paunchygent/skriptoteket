"""Scripting domain provider: script execution and version management handlers."""

from __future__ import annotations

from dishka import Provider, Scope, provide

from skriptoteket.application.scripting.handlers.clear_tool_session_state import (
    ClearToolSessionStateHandler,
)
from skriptoteket.application.scripting.handlers.create_draft_version import (
    CreateDraftVersionHandler,
)
from skriptoteket.application.scripting.handlers.execute_tool_version import (
    ExecuteToolVersionHandler,
)
from skriptoteket.application.scripting.handlers.get_interactive_session_state import (
    GetSessionStateHandler as GetInteractiveSessionStateHandler,
)
from skriptoteket.application.scripting.handlers.get_tool_run import (
    GetRunHandler as GetInteractiveRunHandler,
)
from skriptoteket.application.scripting.handlers.get_tool_session_state import (
    GetToolSessionStateHandler,
)
from skriptoteket.application.scripting.handlers.list_run_artifacts import (
    ListArtifactsHandler as ListInteractiveArtifactsHandler,
)
from skriptoteket.application.scripting.handlers.publish_version import PublishVersionHandler
from skriptoteket.application.scripting.handlers.request_changes import RequestChangesHandler
from skriptoteket.application.scripting.handlers.rollback_version import RollbackVersionHandler
from skriptoteket.application.scripting.handlers.run_active_tool import RunActiveToolHandler
from skriptoteket.application.scripting.handlers.run_sandbox import RunSandboxHandler
from skriptoteket.application.scripting.handlers.save_draft_version import SaveDraftVersionHandler
from skriptoteket.application.scripting.handlers.start_action import StartActionHandler
from skriptoteket.application.scripting.handlers.submit_for_review import SubmitForReviewHandler
from skriptoteket.application.scripting.handlers.update_tool_session_state import (
    UpdateToolSessionStateHandler,
)
from skriptoteket.protocols.catalog import ToolMaintainerRepositoryProtocol, ToolRepositoryProtocol
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.curated_apps import (
    CuratedAppExecutorProtocol,
    CuratedAppRegistryProtocol,
)
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.interactive_tools import (
    GetRunHandlerProtocol,
    GetSessionStateHandlerProtocol,
    ListArtifactsHandlerProtocol,
    StartActionHandlerProtocol,
)
from skriptoteket.protocols.runner import ToolRunnerProtocol
from skriptoteket.protocols.scripting import (
    CreateDraftVersionHandlerProtocol,
    ExecuteToolVersionHandlerProtocol,
    PublishVersionHandlerProtocol,
    RequestChangesHandlerProtocol,
    RollbackVersionHandlerProtocol,
    RunActiveToolHandlerProtocol,
    RunSandboxHandlerProtocol,
    SaveDraftVersionHandlerProtocol,
    SubmitForReviewHandlerProtocol,
    ToolRunRepositoryProtocol,
    ToolVersionRepositoryProtocol,
)
from skriptoteket.protocols.scripting_ui import (
    BackendActionProviderProtocol,
    UiPayloadNormalizerProtocol,
    UiPolicyProviderProtocol,
)
from skriptoteket.protocols.tool_sessions import (
    ClearToolSessionStateHandlerProtocol,
    GetToolSessionStateHandlerProtocol,
    ToolSessionRepositoryProtocol,
    UpdateToolSessionStateHandlerProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class ScriptingProvider(Provider):
    """Provides scripting/execution handlers."""

    @provide(scope=Scope.REQUEST)
    def start_action_handler(
        self,
        uow: UnitOfWorkProtocol,
        tools: ToolRepositoryProtocol,
        curated_apps: CuratedAppRegistryProtocol,
        curated_executor: CuratedAppExecutorProtocol,
        sessions: ToolSessionRepositoryProtocol,
        runs: ToolRunRepositoryProtocol,
        execute: ExecuteToolVersionHandlerProtocol,
        ui_policy_provider: UiPolicyProviderProtocol,
        backend_actions: BackendActionProviderProtocol,
        ui_normalizer: UiPayloadNormalizerProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> StartActionHandlerProtocol:
        return StartActionHandler(
            uow=uow,
            tools=tools,
            curated_apps=curated_apps,
            curated_executor=curated_executor,
            sessions=sessions,
            runs=runs,
            execute=execute,
            ui_policy_provider=ui_policy_provider,
            backend_actions=backend_actions,
            ui_normalizer=ui_normalizer,
            clock=clock,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def get_interactive_session_state_handler(
        self,
        uow: UnitOfWorkProtocol,
        tools: ToolRepositoryProtocol,
        curated_apps: CuratedAppRegistryProtocol,
        sessions: ToolSessionRepositoryProtocol,
        runs: ToolRunRepositoryProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> GetSessionStateHandlerProtocol:
        return GetInteractiveSessionStateHandler(
            uow=uow,
            tools=tools,
            curated_apps=curated_apps,
            sessions=sessions,
            runs=runs,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def get_interactive_run_handler(
        self,
        uow: UnitOfWorkProtocol,
        runs: ToolRunRepositoryProtocol,
    ) -> GetRunHandlerProtocol:
        return GetInteractiveRunHandler(uow=uow, runs=runs)

    @provide(scope=Scope.REQUEST)
    def list_interactive_artifacts_handler(
        self,
        uow: UnitOfWorkProtocol,
        runs: ToolRunRepositoryProtocol,
    ) -> ListArtifactsHandlerProtocol:
        return ListInteractiveArtifactsHandler(uow=uow, runs=runs)

    @provide(scope=Scope.REQUEST)
    def get_tool_session_state_handler(
        self,
        uow: UnitOfWorkProtocol,
        sessions: ToolSessionRepositoryProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> GetToolSessionStateHandlerProtocol:
        return GetToolSessionStateHandler(
            uow=uow,
            sessions=sessions,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def update_tool_session_state_handler(
        self,
        uow: UnitOfWorkProtocol,
        sessions: ToolSessionRepositoryProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> UpdateToolSessionStateHandlerProtocol:
        return UpdateToolSessionStateHandler(
            uow=uow,
            sessions=sessions,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def clear_tool_session_state_handler(
        self,
        uow: UnitOfWorkProtocol,
        sessions: ToolSessionRepositoryProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> ClearToolSessionStateHandlerProtocol:
        return ClearToolSessionStateHandler(
            uow=uow,
            sessions=sessions,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def execute_tool_version_handler(
        self,
        uow: UnitOfWorkProtocol,
        versions: ToolVersionRepositoryProtocol,
        runs: ToolRunRepositoryProtocol,
        runner: ToolRunnerProtocol,
        ui_policy_provider: UiPolicyProviderProtocol,
        backend_actions: BackendActionProviderProtocol,
        ui_normalizer: UiPayloadNormalizerProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> ExecuteToolVersionHandlerProtocol:
        return ExecuteToolVersionHandler(
            uow=uow,
            versions=versions,
            runs=runs,
            runner=runner,
            ui_policy_provider=ui_policy_provider,
            backend_actions=backend_actions,
            ui_normalizer=ui_normalizer,
            clock=clock,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def create_draft_version_handler(
        self,
        uow: UnitOfWorkProtocol,
        tools: ToolRepositoryProtocol,
        maintainers: ToolMaintainerRepositoryProtocol,
        versions: ToolVersionRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> CreateDraftVersionHandlerProtocol:
        return CreateDraftVersionHandler(
            uow=uow,
            tools=tools,
            maintainers=maintainers,
            versions=versions,
            clock=clock,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def save_draft_version_handler(
        self,
        uow: UnitOfWorkProtocol,
        versions: ToolVersionRepositoryProtocol,
        maintainers: ToolMaintainerRepositoryProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> SaveDraftVersionHandlerProtocol:
        return SaveDraftVersionHandler(
            uow=uow,
            versions=versions,
            maintainers=maintainers,
            clock=clock,
            id_generator=id_generator,
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
        versions: ToolVersionRepositoryProtocol,
        maintainers: ToolMaintainerRepositoryProtocol,
        execute: ExecuteToolVersionHandlerProtocol,
    ) -> RunSandboxHandlerProtocol:
        return RunSandboxHandler(
            uow=uow, versions=versions, maintainers=maintainers, execute=execute
        )

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
