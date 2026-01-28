from __future__ import annotations

from uuid import UUID

from skriptoteket.application.scripting.handlers._vault_helpers import (
    build_vault_file_info,
    build_vault_usage_info,
)
from skriptoteket.application.scripting.vault import (
    ListVaultFilesQuery,
    ListVaultFilesResult,
    VaultFileInfo,
)
from skriptoteket.config import Settings
from skriptoteket.domain.catalog.models import Tool
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.models import ToolRun
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

        run_ids = [
            item.source_run_id
            for item in files
            if item.source_kind is VaultFileSourceKind.RUN_ARTIFACT
            and item.source_run_id is not None
        ]

        runs_by_id: dict[UUID, ToolRun] = {}
        tool_ids: set[UUID] = set()
        for run_id in run_ids:
            run = await self._runs.get_by_id(run_id=run_id)
            if run is None:
                continue
            if run.requested_by_user_id != actor.id:
                continue
            runs_by_id[run_id] = run
            tool_ids.add(run.tool_id)

        tools_by_id: dict[UUID, Tool] = {}
        if tool_ids:
            tools_by_id = {
                tool.id: tool for tool in await self._tools.list_by_ids(tool_ids=list(tool_ids))
            }

        def source_label_for(item: VaultFile) -> str | None:
            if (
                item.source_kind is VaultFileSourceKind.RUN_ARTIFACT
                and item.source_run_id is not None
            ):
                run = runs_by_id.get(item.source_run_id)
                if run is None:
                    return None

                curated = self._curated_apps.get_by_tool_id(tool_id=run.tool_id)
                if curated is not None:
                    return curated.title

                tool = tools_by_id.get(run.tool_id)
                if tool is not None:
                    return tool.title

                return None

            if item.source_kind is VaultFileSourceKind.APP_EXPORT:
                app_id = item.source_artifact_id.strip() if item.source_artifact_id else ""
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
