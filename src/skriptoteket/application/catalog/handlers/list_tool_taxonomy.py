from __future__ import annotations

from skriptoteket.application.catalog.queries import (
    ListToolTaxonomyQuery,
    ListToolTaxonomyResult,
)
from skriptoteket.domain.errors import not_found
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.identity.role_guards import require_at_least_role
from skriptoteket.protocols.catalog import ListToolTaxonomyHandlerProtocol, ToolRepositoryProtocol


class ListToolTaxonomyHandler(ListToolTaxonomyHandlerProtocol):
    def __init__(self, *, tools: ToolRepositoryProtocol) -> None:
        self._tools = tools

    async def handle(
        self,
        *,
        actor: User,
        query: ListToolTaxonomyQuery,
    ) -> ListToolTaxonomyResult:
        require_at_least_role(user=actor, role=Role.ADMIN)

        tool = await self._tools.get_by_id(tool_id=query.tool_id)
        if tool is None:
            raise not_found("Tool", str(query.tool_id))

        profession_ids, category_ids = await self._tools.list_tag_ids(
            tool_id=query.tool_id
        )
        return ListToolTaxonomyResult(
            tool_id=query.tool_id,
            profession_ids=profession_ids,
            category_ids=category_ids,
        )
