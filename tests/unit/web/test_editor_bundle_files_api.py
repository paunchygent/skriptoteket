"""Editor API carries gruppgenerator's real bundle files end to end."""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from skriptoteket.application.scripting.commands import (
    CreateDraftVersionResult,
    SaveDraftVersionResult,
)
from skriptoteket.domain.identity.models import Role
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.draft_locks import DraftLockRepositoryProtocol
from skriptoteket.protocols.scripting import (
    CreateDraftVersionHandlerProtocol,
    SaveDraftVersionHandlerProtocol,
    ToolVersionRepositoryProtocol,
)
from skriptoteket.web.api.v1 import editor
from tests.unit.application.scripting.handlers.gruppgenerator_bundle_support import (
    edited_roster_py,
    gruppgenerator_draft,
    gruppgenerator_files,
)
from tests.unit.web.admin_scripting_test_support import _tool, _user


def _unwrap_dishka(fn):
    return getattr(fn, "__dishka_orig_func__", fn)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_editor_boot_for_a_version_returns_every_bundle_file() -> None:
    user = _user(role=Role.ADMIN)
    tool = _tool()
    now = datetime.now(timezone.utc)
    draft = gruppgenerator_draft(
        version_id=uuid4(), tool_id=tool.id, created_by_user_id=user.id, now=now
    )
    tools = AsyncMock()
    tools.get_by_id.return_value = tool
    versions = AsyncMock(spec=ToolVersionRepositoryProtocol)
    versions.get_by_id.return_value = draft
    versions.list_for_tool.return_value = [draft]
    locks = AsyncMock(spec=DraftLockRepositoryProtocol)
    locks.get_for_tool.return_value = None
    clock = Mock(spec=ClockProtocol)
    clock.now.return_value = now

    result = await _unwrap_dishka(editor.get_editor_for_version)(
        version_id=draft.id,
        tools=tools,
        maintainers=AsyncMock(),
        versions_repo=versions,
        locks=locks,
        clock=clock,
        user=user,
    )

    source_code, bundle_files = gruppgenerator_files()
    assert result.source_code == source_code
    assert result.bundle_files == bundle_files
    assert "bundle_files" in result.model_dump(mode="json")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_save_request_json_passes_every_bundle_file_to_the_command() -> None:
    user = _user(role=Role.ADMIN)
    tool = _tool()
    now = datetime.now(timezone.utc)
    previous = gruppgenerator_draft(
        version_id=uuid4(), tool_id=tool.id, created_by_user_id=user.id, now=now
    )
    edited_bundle = {
        **previous.bundle_files,
        "roster.py": edited_roster_py(previous.bundle_files["roster.py"]),
    }
    handler = AsyncMock(spec=SaveDraftVersionHandlerProtocol)
    handler.handle.return_value = SaveDraftVersionResult(version=previous)

    await _unwrap_dishka(editor.save_draft_version)(
        version_id=previous.id,
        payload=editor.SaveDraftVersionRequest.model_validate_json(
            editor.SaveDraftVersionRequest(
                source_code=previous.source_code,
                bundle_files=edited_bundle,
                expected_parent_version_id=previous.id,
            ).model_dump_json()
        ),
        handler=handler,
        user=user,
    )

    command = handler.handle.call_args.kwargs["command"]
    assert command.bundle_files == edited_bundle
    assert "bundle_files" in command.model_fields_set


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_request_without_bundle_files_lets_the_handler_inherit_them() -> None:
    user = _user(role=Role.ADMIN)
    tool = _tool()
    now = datetime.now(timezone.utc)
    created = gruppgenerator_draft(
        version_id=uuid4(), tool_id=tool.id, created_by_user_id=user.id, now=now
    )
    handler = AsyncMock(spec=CreateDraftVersionHandlerProtocol)
    handler.handle.return_value = CreateDraftVersionResult(version=created)

    await _unwrap_dishka(editor.create_draft_version)(
        tool_id=tool.id,
        payload=editor.CreateDraftVersionRequest.model_validate(
            {"source_code": created.source_code, "derived_from_version_id": str(uuid4())}
        ),
        handler=handler,
        user=user,
    )

    command = handler.handle.call_args.kwargs["command"]
    assert "bundle_files" not in command.model_fields_set
