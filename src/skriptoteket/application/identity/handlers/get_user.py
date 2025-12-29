from __future__ import annotations

from skriptoteket.application.identity.admin_users import GetUserQuery, GetUserResult
from skriptoteket.domain.errors import not_found
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.identity.role_guards import require_any_role
from skriptoteket.protocols.identity import GetUserHandlerProtocol, UserRepositoryProtocol


class GetUserHandler(GetUserHandlerProtocol):
    """Fetch a single user for superuser administration."""

    def __init__(self, *, users: UserRepositoryProtocol) -> None:
        self._users = users

    async def handle(self, *, actor: User, query: GetUserQuery) -> GetUserResult:
        require_any_role(user=actor, roles={Role.SUPERUSER})
        user = await self._users.get_by_id(query.user_id)
        if user is None:
            raise not_found("User", str(query.user_id))
        return GetUserResult(user=user)
