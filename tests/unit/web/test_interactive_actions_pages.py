from __future__ import annotations

import uuid
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Protocol, runtime_checkable
from unittest.mock import AsyncMock
from urllib.parse import urlencode

import pytest
from starlette.requests import Request

from skriptoteket.application.scripting.interactive_tools import StartActionResult
from skriptoteket.domain.identity.models import AuthProvider, Role, User
from skriptoteket.domain.scripting.models import RunContext, RunStatus, ToolRun
from skriptoteket.domain.scripting.ui.contract_v2 import (
    UiBooleanField,
    UiEnumField,
    UiEnumOption,
    UiFormAction,
    UiIntegerField,
    UiMultiEnumField,
    UiPayloadV2,
    UiStringField,
)
from skriptoteket.protocols.interactive_tools import StartActionHandlerProtocol
from skriptoteket.protocols.scripting import ToolRunRepositoryProtocol
from skriptoteket.web.pages import tools


@runtime_checkable
class _TemplateProtocol(Protocol):
    name: str


@runtime_checkable
class _TemplateResponseProtocol(Protocol):
    status_code: int
    template: _TemplateProtocol
    context: Mapping[str, object]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _user(*, role: Role) -> User:
    now = _now()
    return User(
        id=uuid.uuid4(),
        email=f"{role.value}@example.com",
        role=role,
        auth_provider=AuthProvider.LOCAL,
        created_at=now,
        updated_at=now,
    )


def _request_form(
    *,
    path: str,
    data: Mapping[str, object],
    hx: bool,
) -> Request:
    body = urlencode(data, doseq=True).encode("utf-8")
    headers: list[tuple[bytes, bytes]] = [
        (b"content-type", b"application/x-www-form-urlencoded"),
        (b"content-length", str(len(body)).encode("ascii")),
    ]
    if hx:
        headers.append((b"hx-request", b"true"))

    scope = {
        "type": "http",
        "method": "POST",
        "path": path,
        "headers": headers,
        "query_string": b"",
    }

    async def receive() -> dict[str, object]:
        nonlocal body
        chunk = body
        body = b""
        return {"type": "http.request", "body": chunk, "more_body": False}

    return Request(scope, receive)


def _run(
    *,
    run_id: uuid.UUID,
    user_id: uuid.UUID,
    tool_id: uuid.UUID,
    action: UiFormAction,
) -> ToolRun:
    now = _now()
    return ToolRun(
        id=run_id,
        tool_id=tool_id,
        version_id=uuid.uuid4(),
        context=RunContext.PRODUCTION,
        requested_by_user_id=user_id,
        status=RunStatus.SUCCEEDED,
        started_at=now,
        finished_at=now,
        workdir_path=str(run_id),
        input_filename="input.bin",
        input_size_bytes=1,
        html_output=None,
        stdout=None,
        stderr=None,
        artifacts_manifest={"artifacts": []},
        error_summary=None,
        ui_payload=UiPayloadV2(outputs=[], next_actions=[action]),
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_start_interactive_action_success_parses_fields_and_renders_new_run() -> None:
    user = _user(role=Role.USER)
    tool_id = uuid.uuid4()
    run_id = uuid.uuid4()
    new_run_id = uuid.uuid4()

    action = UiFormAction(
        action_id="do_it",
        label="Gör det",
        fields=[
            UiStringField(name="name", label="Namn"),
            UiIntegerField(name="count", label="Antal"),
            UiBooleanField(name="confirm", label="Bekräfta"),
            UiEnumField(
                name="choice",
                label="Val",
                options=[UiEnumOption(value="a", label="A"), UiEnumOption(value="b", label="B")],
            ),
            UiMultiEnumField(
                name="multi",
                label="Flera val",
                options=[UiEnumOption(value="x", label="X"), UiEnumOption(value="y", label="Y")],
            ),
        ],
    )

    run = _run(run_id=run_id, user_id=user.id, tool_id=tool_id, action=action)
    new_run = _run(run_id=new_run_id, user_id=user.id, tool_id=tool_id, action=action)

    runs = AsyncMock(spec=ToolRunRepositoryProtocol)
    runs.get_by_id.side_effect = [run, new_run]

    handler = AsyncMock(spec=StartActionHandlerProtocol)
    handler.handle.return_value = StartActionResult(run_id=new_run_id, state_rev=1)

    request = _request_form(
        path="/tools/interactive/start_action",
        hx=True,
        data={
            "_run_id": str(run_id),
            "_context": "default",
            "_action_id": "do_it",
            "_expected_state_rev": "0",
            "name": "Alice",
            "count": "2",
            "confirm": "true",
            "choice": "a",
            "multi": ["x", "y"],
        },
    )

    response = await tools.start_interactive_action.__dishka_orig_func__(  # type: ignore[attr-defined]
        request=request,
        handler=handler,
        runs=runs,
        user=user,
        session=None,
    )

    assert isinstance(response, _TemplateResponseProtocol)
    assert response.status_code == 200
    assert response.template.name == "tools/partials/run_result_with_toast.html"

    called_command = handler.handle.call_args.kwargs["command"]
    assert called_command.tool_id == tool_id
    assert called_command.context == "default"
    assert called_command.action_id == "do_it"
    assert called_command.expected_state_rev == 0
    assert called_command.input == {
        "name": "Alice",
        "count": 2,
        "confirm": True,
        "choice": "a",
        "multi": ["x", "y"],
    }

    assert response.context["run"] == new_run
    assert response.context["interactive_state_rev"] == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_start_interactive_action_invalid_enum_option_renders_error_with_status_400() -> None:
    user = _user(role=Role.USER)
    tool_id = uuid.uuid4()
    run_id = uuid.uuid4()

    action = UiFormAction(
        action_id="do_it",
        label="Gör det",
        fields=[
            UiEnumField(
                name="choice",
                label="Val",
                options=[UiEnumOption(value="a", label="A")],
            ),
        ],
    )
    run = _run(run_id=run_id, user_id=user.id, tool_id=tool_id, action=action)

    runs = AsyncMock(spec=ToolRunRepositoryProtocol)
    runs.get_by_id.return_value = run

    handler = AsyncMock(spec=StartActionHandlerProtocol)

    request = _request_form(
        path="/tools/interactive/start_action",
        hx=True,
        data={
            "_run_id": str(run_id),
            "_context": "default",
            "_action_id": "do_it",
            "_expected_state_rev": "0",
            "choice": "z",
        },
    )

    response = await tools.start_interactive_action.__dishka_orig_func__(  # type: ignore[attr-defined]
        request=request,
        handler=handler,
        runs=runs,
        user=user,
        session=None,
    )

    assert isinstance(response, _TemplateResponseProtocol)
    assert response.status_code == 400
    assert response.template.name == "tools/partials/run_result_with_toast.html"
    assert response.context["action_error"] == "Ogiltig indata."
    handler.handle.assert_not_called()
