from __future__ import annotations

from uuid import UUID

from skriptoteket.application.catalog.commands import (
    UpdateToolTaxonomyCommand,
    UpdateToolTaxonomyResult,
)
from skriptoteket.domain.errors import not_found, validation_error
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.identity.role_guards import require_at_least_role
from skriptoteket.protocols.catalog import (
    CategoryRepositoryProtocol,
    ProfessionRepositoryProtocol,
    ToolRepositoryProtocol,
    UpdateToolTaxonomyHandlerProtocol,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol


def _validate_unique_ids(*, ids: list[UUID], label: str) -> list[UUID]:
    if len(ids) != len(set(ids)):
        raise validation_error(f"Duplicate {label} IDs are not allowed")
    return ids


def _validate_non_empty(*, ids: list[UUID], label: str) -> list[UUID]:
    if not ids:
        raise validation_error(f"At least one {label} is required")
    return ids


class UpdateToolTaxonomyHandler(UpdateToolTaxonomyHandlerProtocol):
    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        tools: ToolRepositoryProtocol,
        professions: ProfessionRepositoryProtocol,
        categories: CategoryRepositoryProtocol,
        clock: ClockProtocol,
    ) -> None:
        self._uow = uow
        self._tools = tools
        self._professions = professions
        self._categories = categories
        self._clock = clock

    async def handle(
        self,
        *,
        actor: User,
        command: UpdateToolTaxonomyCommand,
    ) -> UpdateToolTaxonomyResult:
        require_at_least_role(user=actor, role=Role.ADMIN)

        profession_ids = _validate_non_empty(ids=command.profession_ids, label="profession")
        category_ids = _validate_non_empty(ids=command.category_ids, label="category")
        profession_ids = _validate_unique_ids(ids=profession_ids, label="profession")
        category_ids = _validate_unique_ids(ids=category_ids, label="category")

        async with self._uow:
            tool = await self._tools.get_by_id(tool_id=command.tool_id)
            if tool is None:
                raise not_found("Tool", str(command.tool_id))

            profession_records = await self._professions.list_by_ids(
                profession_ids=profession_ids
            )
            if len(profession_records) != len(set(profession_ids)):
                found = {p.id for p in profession_records}
                missing = [str(pid) for pid in profession_ids if pid not in found]
                raise validation_error(
                    "Unknown profession id(s)",
                    details={"profession_ids": missing},
                )

            category_records = await self._categories.list_by_ids(category_ids=category_ids)
            if len(category_records) != len(set(category_ids)):
                found = {c.id for c in category_records}
                missing = [str(cid) for cid in category_ids if cid not in found]
                raise validation_error(
                    "Unknown category id(s)",
                    details={"category_ids": missing},
                )

            await self._tools.replace_tags(
                tool_id=command.tool_id,
                profession_ids=profession_ids,
                category_ids=category_ids,
                now=self._clock.now(),
            )

        return UpdateToolTaxonomyResult(
            tool_id=command.tool_id,
            profession_ids=profession_ids,
            category_ids=category_ids,
        )
