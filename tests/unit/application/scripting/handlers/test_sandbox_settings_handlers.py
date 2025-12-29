from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from skriptoteket.application.scripting.handlers.resolve_sandbox_settings import (
    ResolveSandboxSettingsHandler,
)
from skriptoteket.application.scripting.handlers.save_sandbox_settings import (
    SaveSandboxSettingsHandler,
)
from skriptoteket.application.scripting.tool_settings import (
    ResolveSandboxSettingsQuery,
    SaveSandboxSettingsCommand,
    ToolSettingsState,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.scripting.draft_locks import DraftLock
from skriptoteket.domain.scripting.ui.contract_v2 import UiActionField, UiStringField
from skriptoteket.protocols.catalog import ToolMaintainerRepositoryProtocol
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.draft_locks import DraftLockRepositoryProtocol
from skriptoteket.protocols.scripting import ToolVersionRepositoryProtocol
from skriptoteket.protocols.tool_settings import ToolSettingsServiceProtocol
from tests.fixtures.identity_fixtures import make_user
from tests.unit.application.scripting.handlers.sandbox_test_support import (
    FakeUow,
    make_tool_version,
)


def _make_lock(
    *,
    tool_id,
    draft_head_id,
    locked_by_user_id,
    now,
    expires_in: timedelta,
) -> DraftLock:
    return DraftLock(
        tool_id=tool_id,
        draft_head_id=draft_head_id,
        locked_by_user_id=locked_by_user_id,
        locked_at=now,
        expires_at=now + expires_in,
        forced_by_user_id=None,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_resolve_sandbox_settings_requires_schema(now) -> None:
    actor = make_user(role=Role.ADMIN)
    version_id = uuid4()

    handler = ResolveSandboxSettingsHandler(
        uow=FakeUow(),
        versions=AsyncMock(spec=ToolVersionRepositoryProtocol),
        maintainers=AsyncMock(spec=ToolMaintainerRepositoryProtocol),
        locks=AsyncMock(spec=DraftLockRepositoryProtocol),
        clock=Mock(spec=ClockProtocol),
        settings_service=AsyncMock(spec=ToolSettingsServiceProtocol),
    )

    with pytest.raises(DomainError) as exc:
        await handler.handle(
            actor=actor,
            query=ResolveSandboxSettingsQuery(
                version_id=version_id,
                settings_schema=None,
            ),
        )

    assert exc.value.code is ErrorCode.VALIDATION_ERROR


@pytest.mark.unit
@pytest.mark.asyncio
async def test_resolve_sandbox_settings_requires_active_lock(now) -> None:
    actor = make_user(role=Role.ADMIN)
    tool_id = uuid4()
    version_id = uuid4()

    uow = FakeUow()
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    locks = AsyncMock(spec=DraftLockRepositoryProtocol)
    clock = Mock(spec=ClockProtocol)
    settings_service = AsyncMock(spec=ToolSettingsServiceProtocol)

    clock.now.return_value = now
    version = make_tool_version(
        version_id=version_id,
        tool_id=tool_id,
        now=now,
        created_by_user_id=actor.id,
    )
    versions.get_by_id.return_value = version
    versions.list_for_tool.return_value = [version]
    locks.get_for_tool.return_value = _make_lock(
        tool_id=tool_id,
        draft_head_id=version_id,
        locked_by_user_id=uuid4(),
        now=now,
        expires_in=timedelta(minutes=10),
    )

    handler = ResolveSandboxSettingsHandler(
        uow=uow,
        versions=versions,
        maintainers=maintainers,
        locks=locks,
        clock=clock,
        settings_service=settings_service,
    )

    schema: list[UiActionField] = [UiStringField(name="theme_color", label="Färgtema")]

    with pytest.raises(DomainError) as exc:
        await handler.handle(
            actor=actor,
            query=ResolveSandboxSettingsQuery(
                version_id=version_id,
                settings_schema=schema,
            ),
        )

    assert exc.value.code is ErrorCode.FORBIDDEN
    settings_service.resolve_sandbox_settings.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_sandbox_settings_calls_service(now) -> None:
    actor = make_user(role=Role.ADMIN)
    tool_id = uuid4()
    version_id = uuid4()

    uow = FakeUow()
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    locks = AsyncMock(spec=DraftLockRepositoryProtocol)
    clock = Mock(spec=ClockProtocol)
    settings_service = AsyncMock(spec=ToolSettingsServiceProtocol)

    clock.now.return_value = now
    version = make_tool_version(
        version_id=version_id,
        tool_id=tool_id,
        now=now,
        created_by_user_id=actor.id,
    )
    versions.get_by_id.return_value = version
    versions.list_for_tool.return_value = [version]
    locks.get_for_tool.return_value = _make_lock(
        tool_id=tool_id,
        draft_head_id=version_id,
        locked_by_user_id=actor.id,
        now=now,
        expires_in=timedelta(minutes=10),
    )

    schema: list[UiActionField] = [UiStringField(name="theme_color", label="Färgtema")]
    settings_service.save_sandbox_settings.return_value = ToolSettingsState(
        tool_id=tool_id,
        schema_version="abc123",
        settings_schema=schema,
        values={"theme_color": "#ff00ff"},
        state_rev=1,
    )

    handler = SaveSandboxSettingsHandler(
        uow=uow,
        versions=versions,
        maintainers=maintainers,
        locks=locks,
        clock=clock,
        settings_service=settings_service,
    )

    result = await handler.handle(
        actor=actor,
        command=SaveSandboxSettingsCommand(
            version_id=version_id,
            settings_schema=schema,
            expected_state_rev=0,
            values={"theme_color": "#ff00ff"},
        ),
    )

    assert result.settings.tool_id == tool_id
    settings_service.save_sandbox_settings.assert_awaited_once_with(
        tool_id=tool_id,
        user_id=actor.id,
        draft_head_id=version_id,
        settings_schema=schema,
        expected_state_rev=0,
        values={"theme_color": "#ff00ff"},
    )
