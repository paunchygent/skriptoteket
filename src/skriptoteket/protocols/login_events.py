from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from skriptoteket.application.identity.login_events import (
    ListLoginEventsQuery,
    ListLoginEventsResult,
)
from skriptoteket.domain.identity.login_events import LoginEvent
from skriptoteket.domain.identity.models import User


class LoginEventRepositoryProtocol(Protocol):
    async def create(self, *, event: LoginEvent) -> LoginEvent: ...

    async def list_by_user(
        self, *, user_id: UUID, limit: int, since: datetime | None = None
    ) -> list[LoginEvent]: ...

    async def delete_expired(self, *, cutoff: datetime) -> int: ...


class ListLoginEventsHandlerProtocol(Protocol):
    async def handle(
        self, *, actor: User, query: ListLoginEventsQuery
    ) -> ListLoginEventsResult: ...
