"""Unit tests for the seating-export readiness smoke helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from skriptoteket.cli.commands import smoke_seating_export_readiness as smoke_command
from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.classroom_planner.models import (
    DEFAULT_ROOM_GRID_COLS,
    DEFAULT_ROOM_GRID_ROWS,
    RoomTemplate,
    Roster,
    Seat,
    Student,
)
from skriptoteket.domain.identity.models import AuthProvider, Role, User


class _AsyncSessionContext:
    async def __aenter__(self) -> object:
        return object()

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


class _FakeRosterRepository:
    def __init__(self, rosters: list[Roster]) -> None:
        self._rosters = rosters

    async def list_by_owner(self, *, owner_user_id):
        return self._rosters


class _FakeTemplateRepository:
    def __init__(self, templates: list[RoomTemplate]) -> None:
        self._templates = templates

    async def list_by_owner(self, *, owner_user_id):
        return self._templates


def _build_actor() -> User:
    now = datetime.now(timezone.utc)
    return User(
        id=uuid4(),
        email="smoke@example.com",
        role=Role.SUPERUSER,
        auth_provider=AuthProvider.LOCAL,
        created_at=now,
        updated_at=now,
    )


def _build_roster(*, owner_user_id, students: list[Student]) -> Roster:
    now = datetime.now(timezone.utc)
    return Roster(
        id=uuid4(),
        owner_user_id=owner_user_id,
        name=smoke_command._SMOKE_ROSTER_NAME,
        students=students,
        created_at=now,
        updated_at=now,
    )


def _build_template(*, owner_user_id, seats: list[Seat]) -> RoomTemplate:
    now = datetime.now(timezone.utc)
    return RoomTemplate(
        id=uuid4(),
        owner_user_id=owner_user_id,
        name=smoke_command._SMOKE_TEMPLATE_NAME,
        grid_cols=DEFAULT_ROOM_GRID_COLS,
        grid_rows=DEFAULT_ROOM_GRID_ROWS,
        seats=seats,
        fixtures=[],
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_ensure_smoke_assets_repairs_named_assets_when_ids_drift(monkeypatch) -> None:
    actor = _build_actor()
    drifting_roster = _build_roster(
        owner_user_id=actor.id,
        students=[Student(id="wrong-student", display_name="Wrong")],
    )
    drifting_template = _build_template(
        owner_user_id=actor.id,
        seats=[Seat(id="wrong-seat", x=0, y=0)],
    )
    roster_repo = _FakeRosterRepository([drifting_roster])
    template_repo = _FakeTemplateRepository([drifting_template])
    update_calls: dict[str, dict[str, object]] = {}

    class _CapturingUpdateRosterHandler:
        def __init__(self, *, uow, rosters, clock) -> None:
            return None

        async def handle(self, **kwargs):
            update_calls["roster"] = kwargs
            return drifting_roster.model_copy(
                update={"students": list(smoke_command._SMOKE_STUDENTS)}
            )

    class _CapturingUpdateTemplateHandler:
        def __init__(self, *, uow, templates, clock) -> None:
            return None

        async def handle(self, **kwargs):
            update_calls["template"] = kwargs
            return drifting_template.model_copy(
                update={
                    "grid_cols": DEFAULT_ROOM_GRID_COLS,
                    "grid_rows": DEFAULT_ROOM_GRID_ROWS,
                    "seats": list(smoke_command._SMOKE_SEATS),
                    "fixtures": [],
                }
            )

    class _UnexpectedCreateHandler:
        def __init__(self, *args, **kwargs) -> None:
            return None

        async def handle(self, **kwargs):
            raise AssertionError(
                "Smoke asset drift should repair existing assets, not create new ones."
            )

    monkeypatch.setattr(smoke_command, "open_session", lambda settings: _AsyncSessionContext())
    monkeypatch.setattr(
        smoke_command,
        "PostgreSQLRosterRepository",
        lambda session: roster_repo,
    )
    monkeypatch.setattr(
        smoke_command,
        "PostgreSQLRoomTemplateRepository",
        lambda session: template_repo,
    )
    monkeypatch.setattr(smoke_command, "CreateRosterHandler", _UnexpectedCreateHandler)
    monkeypatch.setattr(smoke_command, "CreateRoomTemplateHandler", _UnexpectedCreateHandler)
    monkeypatch.setattr(smoke_command, "UpdateRosterHandler", _CapturingUpdateRosterHandler)
    monkeypatch.setattr(
        smoke_command,
        "UpdateRoomTemplateHandler",
        _CapturingUpdateTemplateHandler,
    )

    roster_id, template_id = await smoke_command._ensure_smoke_assets(
        settings=Settings(),
        actor=actor,
    )

    assert roster_id == drifting_roster.id
    assert template_id == drifting_template.id
    assert update_calls["roster"]["students"] == list(smoke_command._SMOKE_STUDENTS)
    assert update_calls["template"]["seats"] == list(smoke_command._SMOKE_SEATS)
