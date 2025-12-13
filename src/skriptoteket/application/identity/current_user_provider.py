from __future__ import annotations

from uuid import UUID

from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.identity import (
    CurrentUserProviderProtocol,
    SessionRepositoryProtocol,
    UserRepositoryProtocol,
)


class CurrentUserProvider(CurrentUserProviderProtocol):
    def __init__(
        self,
        *,
        users: UserRepositoryProtocol,
        sessions: SessionRepositoryProtocol,
        clock: ClockProtocol,
    ) -> None:
        self._users = users
        self._sessions = sessions
        self._clock = clock

    async def get_current_user(self, *, session_id: UUID | None) -> User | None:
        if session_id is None:
            return None

        session = await self._sessions.get_by_id(session_id)
        if session is None or session.revoked_at is not None:
            return None

        if session.expires_at <= self._clock.now():
            return None

        user = await self._users.get_by_id(session.user_id)
        if user is None or not user.is_active:
            return None

        return user
