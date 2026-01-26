from __future__ import annotations

from skriptoteket.application.scripting.handlers._vault_helpers import (
    build_vault_file_info,
    build_vault_usage_info,
)
from skriptoteket.application.scripting.vault import ListVaultFilesQuery, ListVaultFilesResult
from skriptoteket.config import Settings
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from skriptoteket.protocols.vault import (
    ListVaultFilesHandlerProtocol,
    VaultFileRepositoryProtocol,
    VaultUsageRepositoryProtocol,
)


class ListVaultFilesHandler(ListVaultFilesHandlerProtocol):
    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        vault_files: VaultFileRepositoryProtocol,
        vault_usage: VaultUsageRepositoryProtocol,
        settings: Settings,
    ) -> None:
        self._uow = uow
        self._vault_files = vault_files
        self._vault_usage = vault_usage
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

        next_cursor = str(offset + limit) if has_more else None

        return ListVaultFilesResult(
            state=query.state,
            search=query.search,
            sort=query.sort,
            files=[build_vault_file_info(vault_file=item) for item in files],
            usage=build_vault_usage_info(usage=usage, settings=self._settings),
            next_cursor=next_cursor,
        )
