from __future__ import annotations

from skriptoteket.application.scripting.file_refs import (
    FileRefInfo,
    ListToolFileRefsQuery,
    ListToolFileRefsResult,
)
from skriptoteket.domain.errors import not_found
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.identity.role_guards import require_at_least_role
from skriptoteket.domain.scripting.tool_sessions import normalize_tool_session_context
from skriptoteket.protocols.catalog import ToolRepositoryProtocol
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.file_refs import FileRefResolverProtocol
from skriptoteket.protocols.scripting import ListToolFileRefsHandlerProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class ListToolFileRefsHandler(ListToolFileRefsHandlerProtocol):
    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        tools: ToolRepositoryProtocol,
        curated_apps: CuratedAppRegistryProtocol,
        file_refs: FileRefResolverProtocol,
    ) -> None:
        self._uow = uow
        self._tools = tools
        self._curated_apps = curated_apps
        self._file_refs = file_refs

    async def handle(
        self,
        *,
        actor: User,
        query: ListToolFileRefsQuery,
    ) -> ListToolFileRefsResult:
        context = normalize_tool_session_context(context=query.context)

        async with self._uow:
            tool = await self._tools.get_by_id(tool_id=query.tool_id)
            if tool is not None and tool.is_published and tool.active_version_id is not None:
                pass
            else:
                app = self._curated_apps.get_by_tool_id(tool_id=query.tool_id)
                if app is None:
                    raise not_found("Tool", str(query.tool_id))
                require_at_least_role(user=actor, role=app.min_role)

        refs = await self._file_refs.list_refs(
            tool_id=query.tool_id,
            user_id=actor.id,
            context=context,
        )

        return ListToolFileRefsResult(
            tool_id=query.tool_id,
            context=context,
            files=[
                FileRefInfo(
                    ref=item.ref,
                    name=item.name,
                    bytes=item.bytes,
                    field=item.field,
                )
                for item in refs
            ],
        )
