from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar
from uuid import UUID

from skriptoteket.domain.curated_apps.models import CuratedAppDefinition
from skriptoteket.domain.errors import not_found
from skriptoteket.domain.identity.models import Session, User
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.identity import CurrentUserProviderProtocol, SessionRepositoryProtocol
from skriptoteket.protocols.reagent_prep_chef import ReagentPrepChefSdsStoreProtocol

TResult = TypeVar("TResult")
TCommand = TypeVar("TCommand")


class FixedClock(ClockProtocol):
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


class StubCurrentUserProvider(CurrentUserProviderProtocol):
    def __init__(self) -> None:
        self.user: User | None = None
        self.calls: list[UUID | None] = []

    async def get_current_user(self, *, session_id: UUID | None) -> User | None:
        self.calls.append(session_id)
        return self.user


class StubSessionRepository(SessionRepositoryProtocol):
    def __init__(self) -> None:
        self.sessions: dict[UUID, Session] = {}

    async def create(self, *, session: Session) -> None:
        self.sessions[session.id] = session

    async def get_by_id(self, session_id: UUID) -> Session | None:
        return self.sessions.get(session_id)

    async def revoke(self, *, session_id: UUID) -> None:
        self.sessions.pop(session_id, None)

    async def count_active(self, *, now: datetime) -> int:
        return sum(1 for session in self.sessions.values() if session.expires_at > now)

    async def sync_ai_settings_for_user(
        self,
        *,
        user_id: UUID,
        allow_remote_fallback: bool | None,
        inline_completion_provider: str | None,
        now: datetime,
    ) -> None:
        return None


class StubCuratedAppRegistry(CuratedAppRegistryProtocol):
    def __init__(self, *, app: CuratedAppDefinition) -> None:
        self._app = app

    def list_all(self) -> list[CuratedAppDefinition]:
        return [self._app]

    def get_by_app_id(self, *, app_id: str) -> CuratedAppDefinition | None:
        return self._app if self._app.app_id == app_id else None

    def get_by_tool_id(self, *, tool_id: UUID) -> CuratedAppDefinition | None:
        return self._app if self._app.tool_id == tool_id else None


class StubActorHandler(Generic[TResult]):
    def __init__(self) -> None:
        self.result: TResult | None = None
        self.calls: list[User] = []

    def set_result(self, result: TResult) -> None:
        self.result = result

    async def handle(self, *, actor: User) -> TResult:
        self.calls.append(actor)
        if self.result is None:
            raise AssertionError("StubActorHandler.result must be set before calling handle().")
        return self.result


class StubActorCommandHandler(Generic[TCommand, TResult]):
    def __init__(self) -> None:
        self.result: TResult | None = None
        self.calls: list[tuple[User, TCommand]] = []

    def set_result(self, result: TResult) -> None:
        self.result = result

    async def handle(self, *, actor: User, command: TCommand, **_: object) -> TResult:
        self.calls.append((actor, command))
        if self.result is None:
            raise AssertionError(
                "StubActorCommandHandler.result must be set before calling handle()."
            )
        return self.result


class StubSdsStore(ReagentPrepChefSdsStoreProtocol):
    def __init__(self) -> None:
        self.files: dict[str, tuple[str, bytes, str]] = {}
        self.calls: list[str] = []

    def add(self, *, sds_ref: str, filename: str, content: bytes, media_type: str) -> None:
        self.files[sds_ref] = (filename, content, media_type)

    def get(self, *, sds_ref: str) -> tuple[str, bytes, str]:
        self.calls.append(sds_ref)
        stored = self.files.get(sds_ref)
        if stored is None:
            raise not_found("SDS", sds_ref)
        return stored
