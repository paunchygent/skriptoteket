"""Scripting domain provider: script execution and version management handlers."""

from __future__ import annotations

from dishka import Provider, Scope, provide

from skriptoteket.application.scripting.handlers.clear_tool_session_state import (
    ClearToolSessionStateHandler,
)
from skriptoteket.application.scripting.handlers.delete_session_files import (
    DeleteSessionFilesHandler,
)
from skriptoteket.application.scripting.handlers.delete_vault_file import DeleteVaultFileHandler
from skriptoteket.application.scripting.handlers.download_vault_file import (
    DownloadVaultFileHandler,
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
from skriptoteket.application.scripting.handlers.get_tool_settings import GetToolSettingsHandler
from skriptoteket.application.scripting.handlers.list_run_artifacts import (
    ListArtifactsHandler as ListInteractiveArtifactsHandler,
)
from skriptoteket.application.scripting.handlers.list_session_files import (
    ListSessionFilesHandler,
)
from skriptoteket.application.scripting.handlers.list_tool_file_refs import (
    ListToolFileRefsHandler,
)
from skriptoteket.application.scripting.handlers.list_vault_files import ListVaultFilesHandler
from skriptoteket.application.scripting.handlers.restore_vault_file import RestoreVaultFileHandler
from skriptoteket.application.scripting.handlers.run_active_tool import RunActiveToolHandler
from skriptoteket.application.scripting.handlers.save_vault_file import SaveVaultFileHandler
from skriptoteket.application.scripting.handlers.start_action import StartActionHandler
from skriptoteket.application.scripting.handlers.update_tool_session_state import (
    UpdateToolSessionStateHandler,
)
from skriptoteket.application.scripting.handlers.update_tool_settings import (
    UpdateToolSettingsHandler,
)
from skriptoteket.config import Settings
from skriptoteket.protocols.catalog import ToolRepositoryProtocol
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.curated_apps import (
    CuratedAppExecutorProtocol,
    CuratedAppRegistryProtocol,
)
from skriptoteket.protocols.execution_queue import ToolRunJobRepositoryProtocol
from skriptoteket.protocols.file_refs import FileRefResolverProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.interactive_tools import (
    DeleteSessionFilesHandlerProtocol,
    GetRunHandlerProtocol,
    GetSessionStateHandlerProtocol,
    ListArtifactsHandlerProtocol,
    ListSessionFilesHandlerProtocol,
    StartActionHandlerProtocol,
)
from skriptoteket.protocols.promotions import PromotionApplierProtocol
from skriptoteket.protocols.run_inputs import RunInputStorageProtocol
from skriptoteket.protocols.runner import ArtifactManagerProtocol, ToolRunnerProtocol
from skriptoteket.protocols.scripting import (
    ExecuteToolVersionHandlerProtocol,
    ListToolFileRefsHandlerProtocol,
    RunActiveToolHandlerProtocol,
    ToolRunRepositoryProtocol,
    ToolVersionRepositoryProtocol,
)
from skriptoteket.protocols.scripting_ui import (
    BackendActionProviderProtocol,
    UiPayloadNormalizerProtocol,
    UiPolicyProviderProtocol,
)
from skriptoteket.protocols.session_files import SessionFileStorageProtocol
from skriptoteket.protocols.tool_sessions import (
    ClearToolSessionStateHandlerProtocol,
    GetToolSessionStateHandlerProtocol,
    ToolSessionRepositoryProtocol,
    UpdateToolSessionStateHandlerProtocol,
)
from skriptoteket.protocols.tool_settings import (
    GetToolSettingsHandlerProtocol,
    UpdateToolSettingsHandlerProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from skriptoteket.protocols.vault import (
    DeleteVaultFileHandlerProtocol,
    DownloadVaultFileHandlerProtocol,
    ListVaultFilesHandlerProtocol,
    RestoreVaultFileHandlerProtocol,
    SaveVaultFileHandlerProtocol,
    VaultFileRepositoryProtocol,
    VaultStorageProtocol,
    VaultUsageRepositoryProtocol,
)


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
        session_files: SessionFileStorageProtocol,
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
            session_files=session_files,
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
        tools: ToolRepositoryProtocol,
        curated_apps: CuratedAppRegistryProtocol,
    ) -> GetRunHandlerProtocol:
        return GetInteractiveRunHandler(
            uow=uow,
            runs=runs,
            tools=tools,
            curated_apps=curated_apps,
        )

    @provide(scope=Scope.REQUEST)
    def list_interactive_artifacts_handler(
        self,
        uow: UnitOfWorkProtocol,
        runs: ToolRunRepositoryProtocol,
    ) -> ListArtifactsHandlerProtocol:
        return ListInteractiveArtifactsHandler(uow=uow, runs=runs)

    @provide(scope=Scope.REQUEST)
    def list_session_files_handler(
        self,
        uow: UnitOfWorkProtocol,
        tools: ToolRepositoryProtocol,
        curated_apps: CuratedAppRegistryProtocol,
        session_files: SessionFileStorageProtocol,
    ) -> ListSessionFilesHandlerProtocol:
        return ListSessionFilesHandler(
            uow=uow,
            tools=tools,
            curated_apps=curated_apps,
            session_files=session_files,
        )

    @provide(scope=Scope.REQUEST)
    def delete_session_files_handler(
        self,
        uow: UnitOfWorkProtocol,
        tools: ToolRepositoryProtocol,
        curated_apps: CuratedAppRegistryProtocol,
        session_files: SessionFileStorageProtocol,
    ) -> DeleteSessionFilesHandlerProtocol:
        return DeleteSessionFilesHandler(
            uow=uow,
            tools=tools,
            curated_apps=curated_apps,
            session_files=session_files,
        )

    @provide(scope=Scope.REQUEST)
    def list_tool_file_refs_handler(
        self,
        uow: UnitOfWorkProtocol,
        tools: ToolRepositoryProtocol,
        curated_apps: CuratedAppRegistryProtocol,
        file_refs: FileRefResolverProtocol,
    ) -> ListToolFileRefsHandlerProtocol:
        return ListToolFileRefsHandler(
            uow=uow,
            tools=tools,
            curated_apps=curated_apps,
            file_refs=file_refs,
        )

    @provide(scope=Scope.REQUEST)
    def list_vault_files_handler(
        self,
        uow: UnitOfWorkProtocol,
        runs: ToolRunRepositoryProtocol,
        tools: ToolRepositoryProtocol,
        curated_apps: CuratedAppRegistryProtocol,
        vault_files: VaultFileRepositoryProtocol,
        vault_usage: VaultUsageRepositoryProtocol,
        vault_storage: VaultStorageProtocol,
        settings: Settings,
    ) -> ListVaultFilesHandlerProtocol:
        return ListVaultFilesHandler(
            uow=uow,
            runs=runs,
            tools=tools,
            curated_apps=curated_apps,
            vault_files=vault_files,
            vault_usage=vault_usage,
            vault_storage=vault_storage,
            settings=settings,
        )

    @provide(scope=Scope.REQUEST)
    def save_vault_file_handler(
        self,
        uow: UnitOfWorkProtocol,
        runs: ToolRunRepositoryProtocol,
        artifacts: ArtifactManagerProtocol,
        vault_files: VaultFileRepositoryProtocol,
        vault_usage: VaultUsageRepositoryProtocol,
        vault_storage: VaultStorageProtocol,
        settings: Settings,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> SaveVaultFileHandlerProtocol:
        return SaveVaultFileHandler(
            uow=uow,
            runs=runs,
            artifacts=artifacts,
            vault_files=vault_files,
            vault_usage=vault_usage,
            vault_storage=vault_storage,
            settings=settings,
            clock=clock,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def delete_vault_file_handler(
        self,
        uow: UnitOfWorkProtocol,
        vault_files: VaultFileRepositoryProtocol,
        vault_usage: VaultUsageRepositoryProtocol,
        clock: ClockProtocol,
    ) -> DeleteVaultFileHandlerProtocol:
        return DeleteVaultFileHandler(
            uow=uow,
            vault_files=vault_files,
            vault_usage=vault_usage,
            clock=clock,
        )

    @provide(scope=Scope.REQUEST)
    def restore_vault_file_handler(
        self,
        uow: UnitOfWorkProtocol,
        vault_files: VaultFileRepositoryProtocol,
        vault_usage: VaultUsageRepositoryProtocol,
        settings: Settings,
        clock: ClockProtocol,
    ) -> RestoreVaultFileHandlerProtocol:
        return RestoreVaultFileHandler(
            uow=uow,
            vault_files=vault_files,
            vault_usage=vault_usage,
            settings=settings,
            clock=clock,
        )

    @provide(scope=Scope.REQUEST)
    def download_vault_file_handler(
        self,
        uow: UnitOfWorkProtocol,
        vault_files: VaultFileRepositoryProtocol,
        vault_storage: VaultStorageProtocol,
    ) -> DownloadVaultFileHandlerProtocol:
        return DownloadVaultFileHandler(
            uow=uow,
            vault_files=vault_files,
            vault_storage=vault_storage,
        )

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
    def get_tool_settings_handler(
        self,
        uow: UnitOfWorkProtocol,
        tools: ToolRepositoryProtocol,
        versions: ToolVersionRepositoryProtocol,
        sessions: ToolSessionRepositoryProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> GetToolSettingsHandlerProtocol:
        return GetToolSettingsHandler(
            uow=uow,
            tools=tools,
            versions=versions,
            sessions=sessions,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def update_tool_settings_handler(
        self,
        uow: UnitOfWorkProtocol,
        tools: ToolRepositoryProtocol,
        versions: ToolVersionRepositoryProtocol,
        sessions: ToolSessionRepositoryProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> UpdateToolSettingsHandlerProtocol:
        return UpdateToolSettingsHandler(
            uow=uow,
            tools=tools,
            versions=versions,
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
        settings: Settings,
        versions: ToolVersionRepositoryProtocol,
        runs: ToolRunRepositoryProtocol,
        jobs: ToolRunJobRepositoryProtocol,
        run_inputs: RunInputStorageProtocol,
        sessions: ToolSessionRepositoryProtocol,
        runner: ToolRunnerProtocol,
        file_refs: FileRefResolverProtocol,
        promotion_applier: PromotionApplierProtocol,
        ui_policy_provider: UiPolicyProviderProtocol,
        backend_actions: BackendActionProviderProtocol,
        ui_normalizer: UiPayloadNormalizerProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> ExecuteToolVersionHandlerProtocol:
        return ExecuteToolVersionHandler(
            uow=uow,
            settings=settings,
            versions=versions,
            runs=runs,
            jobs=jobs,
            run_inputs=run_inputs,
            sessions=sessions,
            runner=runner,
            file_refs=file_refs,
            promotion_applier=promotion_applier,
            ui_policy_provider=ui_policy_provider,
            backend_actions=backend_actions,
            ui_normalizer=ui_normalizer,
            clock=clock,
            id_generator=id_generator,
        )

    @provide(scope=Scope.REQUEST)
    def run_active_tool_handler(
        self,
        uow: UnitOfWorkProtocol,
        tools: ToolRepositoryProtocol,
        versions: ToolVersionRepositoryProtocol,
        execute: ExecuteToolVersionHandlerProtocol,
        sessions: ToolSessionRepositoryProtocol,
        id_generator: IdGeneratorProtocol,
        session_files: SessionFileStorageProtocol,
    ) -> RunActiveToolHandlerProtocol:
        return RunActiveToolHandler(
            uow=uow,
            tools=tools,
            versions=versions,
            execute=execute,
            sessions=sessions,
            id_generator=id_generator,
            session_files=session_files,
        )
