from __future__ import annotations

from skriptoteket.application.identity.admin_users import ListUsersQuery, ListUsersResult
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.identity.role_guards import require_any_role
from skriptoteket.protocols.identity import ListUsersHandlerProtocol, UserRepositoryProtocol


class ListUsersHandler(ListUsersHandlerProtocol):
    """List users for superuser administration."""

    def __init__(self, *, users: UserRepositoryProtocol) -> None:
        self._users = users

    async def handle(self, *, actor: User, query: ListUsersQuery) -> ListUsersResult:
        require_any_role(user=actor, roles={Role.SUPERUSER})
        users = await self._users.list_users(limit=query.limit, offset=query.offset)
        total = await self._users.count_all()
        return ListUsersResult(users=users, total=total)
