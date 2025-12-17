from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from skriptoteket.application.catalog.commands import AssignMaintainerCommand
from skriptoteket.application.catalog.handlers.assign_maintainer import AssignMaintainerHandler
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role
from skriptoteket.protocols.catalog import (
    ToolMaintainerAuditRepositoryProtocol,
    ToolMaintainerRepositoryProtocol,
    ToolRepositoryProtocol,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.identity import UserRepositoryProtocol
from tests.fixtures.application_fixtures import FakeUow
from tests.fixtures.catalog_fixtures import make_tool
from tests.fixtures.identity_fixtures import make_user


@pytest.mark.unit
@pytest.mark.asyncio
async def test_assign_maintainer_requires_admin(now: datetime) -> None:
    actor = make_user(role=Role.CONTRIBUTOR)
    tool = make_tool(now=now)
    target = make_user(role=Role.CONTRIBUTOR)

    uow = FakeUow()
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    users = AsyncMock(spec=UserRepositoryProtocol)
    audit = AsyncMock(spec=ToolMaintainerAuditRepositoryProtocol)
    clock = Mock(spec=ClockProtocol, now=Mock(return_value=now))
    id_generator = Mock(spec=IdGeneratorProtocol)

    handler = AssignMaintainerHandler(
        uow=uow,
        tools=tools,
        maintainers=maintainers,
        users=users,
        audit=audit,
        clock=clock,
        id_generator=id_generator,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=AssignMaintainerCommand(tool_id=tool.id, user_id=target.id),
        )

    assert exc_info.value.code is ErrorCode.FORBIDDEN
    assert uow.entered is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_assign_maintainer_rejects_missing_tool(now: datetime) -> None:
    actor = make_user(role=Role.ADMIN)
    tool_id = uuid4()
    target = make_user(role=Role.CONTRIBUTOR)

    uow = FakeUow()
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.get_by_id.return_value = None

    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    users = AsyncMock(spec=UserRepositoryProtocol)
    audit = AsyncMock(spec=ToolMaintainerAuditRepositoryProtocol)
    clock = Mock(spec=ClockProtocol, now=Mock(return_value=now))
    id_generator = Mock(spec=IdGeneratorProtocol, new_uuid=Mock(return_value=uuid4()))

    handler = AssignMaintainerHandler(
        uow=uow,
        tools=tools,
        maintainers=maintainers,
        users=users,
        audit=audit,
        clock=clock,
        id_generator=id_generator,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=AssignMaintainerCommand(tool_id=tool_id, user_id=target.id),
        )

    assert exc_info.value.code is ErrorCode.NOT_FOUND
    assert uow.entered is True
    assert uow.exited is True
    users.get_by_id.assert_not_called()
    maintainers.add_maintainer.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_assign_maintainer_rejects_missing_user(now: datetime) -> None:
    actor = make_user(role=Role.ADMIN)
    tool = make_tool(now=now)
    user_id = uuid4()

    uow = FakeUow()
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.get_by_id.return_value = tool

    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    users = AsyncMock(spec=UserRepositoryProtocol)
    users.get_by_id.return_value = None

    audit = AsyncMock(spec=ToolMaintainerAuditRepositoryProtocol)
    clock = Mock(spec=ClockProtocol, now=Mock(return_value=now))
    id_generator = Mock(spec=IdGeneratorProtocol, new_uuid=Mock(return_value=uuid4()))

    handler = AssignMaintainerHandler(
        uow=uow,
        tools=tools,
        maintainers=maintainers,
        users=users,
        audit=audit,
        clock=clock,
        id_generator=id_generator,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=AssignMaintainerCommand(tool_id=tool.id, user_id=user_id),
        )

    assert exc_info.value.code is ErrorCode.NOT_FOUND
    assert uow.entered is True
    assert uow.exited is True
    maintainers.is_maintainer.assert_not_called()
    maintainers.add_maintainer.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_assign_maintainer_rejects_user_role_below_contributor(now: datetime) -> None:
    actor = make_user(role=Role.ADMIN)
    tool = make_tool(now=now)
    target = make_user(role=Role.USER)

    uow = FakeUow()
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.get_by_id.return_value = tool

    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    users = AsyncMock(spec=UserRepositoryProtocol)
    users.get_by_id.return_value = target

    audit = AsyncMock(spec=ToolMaintainerAuditRepositoryProtocol)
    clock = Mock(spec=ClockProtocol, now=Mock(return_value=now))
    id_generator = Mock(spec=IdGeneratorProtocol, new_uuid=Mock(return_value=uuid4()))

    handler = AssignMaintainerHandler(
        uow=uow,
        tools=tools,
        maintainers=maintainers,
        users=users,
        audit=audit,
        clock=clock,
        id_generator=id_generator,
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(
            actor=actor,
            command=AssignMaintainerCommand(tool_id=tool.id, user_id=target.id),
        )

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert uow.entered is True
    assert uow.exited is True
    maintainers.is_maintainer.assert_not_called()
    maintainers.add_maintainer.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_assign_maintainer_is_idempotent_for_existing_maintainer(now: datetime) -> None:
    actor = make_user(role=Role.ADMIN)
    tool = make_tool(now=now)
    target = make_user(role=Role.CONTRIBUTOR)

    uow = FakeUow()
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.get_by_id.return_value = tool

    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    maintainers.is_maintainer.return_value = True

    users = AsyncMock(spec=UserRepositoryProtocol)
    users.get_by_id.return_value = target

    audit = AsyncMock(spec=ToolMaintainerAuditRepositoryProtocol)
    clock = Mock(spec=ClockProtocol, now=Mock(return_value=now))
    id_generator = Mock(spec=IdGeneratorProtocol, new_uuid=Mock(return_value=uuid4()))

    handler = AssignMaintainerHandler(
        uow=uow,
        tools=tools,
        maintainers=maintainers,
        users=users,
        audit=audit,
        clock=clock,
        id_generator=id_generator,
    )

    result = await handler.handle(
        actor=actor,
        command=AssignMaintainerCommand(tool_id=tool.id, user_id=target.id),
    )

    assert result.tool_id == tool.id
    assert result.user_id == target.id
    maintainers.add_maintainer.assert_not_called()
    audit.log_action.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_assign_maintainer_adds_maintainer_and_logs_audit(now: datetime) -> None:
    actor = make_user(role=Role.ADMIN, user_id=uuid4())
    tool = make_tool(now=now)
    target = make_user(role=Role.CONTRIBUTOR, user_id=uuid4())
    log_id = uuid4()

    uow = FakeUow()
    tools = AsyncMock(spec=ToolRepositoryProtocol)
    tools.get_by_id.return_value = tool

    maintainers = AsyncMock(spec=ToolMaintainerRepositoryProtocol)
    maintainers.is_maintainer.return_value = False

    users = AsyncMock(spec=UserRepositoryProtocol)
    users.get_by_id.return_value = target

    audit = AsyncMock(spec=ToolMaintainerAuditRepositoryProtocol)
    clock = Mock(spec=ClockProtocol, now=Mock(return_value=now))
    id_generator = Mock(spec=IdGeneratorProtocol, new_uuid=Mock(return_value=log_id))

    handler = AssignMaintainerHandler(
        uow=uow,
        tools=tools,
        maintainers=maintainers,
        users=users,
        audit=audit,
        clock=clock,
        id_generator=id_generator,
    )

    result = await handler.handle(
        actor=actor,
        command=AssignMaintainerCommand(tool_id=tool.id, user_id=target.id, reason="Test reason"),
    )

    assert result.tool_id == tool.id
    assert result.user_id == target.id
    assert uow.entered is True
    assert uow.exited is True

    maintainers.add_maintainer.assert_awaited_once_with(tool_id=tool.id, user_id=target.id)
    audit.log_action.assert_awaited_once_with(
        log_id=log_id,
        tool_id=tool.id,
        user_id=target.id,
        action="assigned",
        performed_by_user_id=actor.id,
        performed_at=now,
        reason="Test reason",
    )
