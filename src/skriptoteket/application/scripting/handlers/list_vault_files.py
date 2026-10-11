from __future__ import annotations

from uuid import UUID

from skriptoteket.application.scripting.handlers._vault_helpers import (
    app_id_from_source_artifact_id,
    build_vault_file_info,
    build_vault_usage_info,
)
from skriptoteket.application.scripting.vault import (
    ListVaultFilesQuery,
    ListVaultFilesResult,
    VaultFileInfo,
)
from skriptoteket.config import Settings
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.vault import VaultFile, VaultFileSourceKind
from skriptoteket.protocols.catalog import ToolRepositoryProtocol
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.scripting import ToolRunRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from skriptoteket.protocols.vault import (
    ListVaultFilesHandlerProtocol,
    VaultFileRepositoryProtocol,
    VaultStorageProtocol,
    VaultUsageRepositoryProtocol,
)


class ListVaultFilesHandler(ListVaultFilesHandlerProtocol):
    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        runs: ToolRunRepositoryProtocol,
        tools: ToolRepositoryProtocol,
        curated_apps: CuratedAppRegistryProtocol,
        vault_files: VaultFileRepositoryProtocol,
        vault_usage: VaultUsageRepositoryProtocol,
        vault_storage: VaultStorageProtocol,
        settings: Settings,
    ) -> None:
        self._uow = uow
        self._runs = runs
        self._tools = tools
        self._curated_apps = curated_apps
        self._vault_files = vault_files
        self._vault_usage = vault_usage
        self._vault_storage = vault_storage
        self._settings = settings

    async def handle(self, *, actor: User, query: ListVaultFilesQuery) -> ListVaultFilesResult:
        limit = max(1, query.limit)
        offset = max(0, query.cursor or 0)
        fetch_limit = limit + 1

        async with self._uow:
            files = await self._vault_files.list_for_user(
                user_id=actor.id,
                state=query.state,
                search=query.search,
                sort=query.sort,
                limit=fetch_limit,
                offset=offset,
            )
            usage = await self._vault_usage.get(user_id=actor.id)

            has_more = len(files) > limit
            if has_more:
                files = files[:limit]

            file_infos = await self._build_file_infos(actor=actor, files=files)

        return ListVaultFilesResult(
            state=query.state,
            search=query.search,
            sort=query.sort,
            files=file_infos,
            usage=build_vault_usage_info(usage=usage, settings=self._settings),
            next_cursor=str(offset + limit) if has_more else None,
        )

    async def _build_file_infos(
        self, *, actor: User, files: list[VaultFile]
    ) -> list[VaultFileInfo]:
        if not files:
            return []

        missing_on_disk_ids: set[UUID] = set()
        for item in files:
            exists = await self._vault_storage.exists_file(user_id=actor.id, file_id=item.id)
            if not exists:
                missing_on_disk_ids.add(item.id)

        run_ids = {
            item.source_run_id
            for item in files
            if item.source_kind is VaultFileSourceKind.RUN_ARTIFACT
            and item.source_run_id is not None
        }

        tool_id_by_run_id: dict[UUID, UUID] = {}
        for run_id in run_ids:
            run = await self._runs.get_by_id(run_id=run_id)
            if run is not None and run.requested_by_user_id == actor.id:
                tool_id_by_run_id[run_id] = run.tool_id

        title_by_tool_id: dict[UUID, str] = {}
        catalog_tool_ids: list[UUID] = []
        for tool_id in set(tool_id_by_run_id.values()):
            curated = self._curated_apps.get_by_tool_id(tool_id=tool_id)
            if curated is not None:
                title_by_tool_id[tool_id] = curated.title
            else:
                catalog_tool_ids.append(tool_id)
        if catalog_tool_ids:
            for tool in await self._tools.list_by_ids(tool_ids=catalog_tool_ids):
                title_by_tool_id[tool.id] = tool.title

        def source_label_for(item: VaultFile) -> str | None:
            if (
                item.source_kind is VaultFileSourceKind.RUN_ARTIFACT
                and item.source_run_id is not None
            ):
                tool_id = tool_id_by_run_id.get(item.source_run_id)
                if tool_id is None:
                    return None
                return title_by_tool_id.get(tool_id)

            if item.source_kind is VaultFileSourceKind.APP_EXPORT:
                app_id = app_id_from_source_artifact_id(item.source_artifact_id)
                if app_id:
                    app = self._curated_apps.get_by_app_id(app_id=app_id)
                    if app is not None:
                        return app.title
                return "App-export"

            return None

        return [
            build_vault_file_info(
                vault_file=item,
                source_label=source_label_for(item),
                is_missing_on_disk=item.id in missing_on_disk_ids,
            )
            for item in files
        ]
