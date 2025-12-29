from __future__ import annotations

from datetime import timedelta

from skriptoteket.application.identity.login_events import (
    ListLoginEventsQuery,
    ListLoginEventsResult,
)
from skriptoteket.config import Settings
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.domain.identity.role_guards import require_any_role
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.login_events import (
    ListLoginEventsHandlerProtocol,
    LoginEventRepositoryProtocol,
)


class ListLoginEventsHandler(ListLoginEventsHandlerProtocol):
    """List login events for a user (superuser only)."""

    def __init__(
        self,
        *,
        settings: Settings,
        clock: ClockProtocol,
        login_events: LoginEventRepositoryProtocol,
    ) -> None:
        self._settings = settings
        self._clock = clock
        self._login_events = login_events

    async def handle(self, *, actor: User, query: ListLoginEventsQuery) -> ListLoginEventsResult:
        require_any_role(user=actor, roles={Role.SUPERUSER})
        cutoff = self._clock.now() - timedelta(days=self._settings.LOGIN_EVENTS_RETENTION_DAYS)
        events = await self._login_events.list_by_user(
            user_id=query.user_id,
            limit=query.limit,
            since=cutoff,
        )
        return ListLoginEventsResult(events=events)
