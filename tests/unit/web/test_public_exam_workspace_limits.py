"""Public exam workspace limits route: the exam size cap comes from its backend owner.

Repair for review F4: both modes read the exam size limit from this public
route instead of a handwritten frontend constant. The value is the injected
settings' ``VAULT_MAX_FILE_BYTES`` read at request time, so a test override
of the setting proves the value is owned by the backend, not a constant.
"""

from __future__ import annotations

import httpx
import pytest
from fastapi import FastAPI

from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.models import CuratedAppPublicRuntimeStatus
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.public_request_limits import PublicRequestBucket
from tests.unit.web import (
    public_exam_workspace_command_routes_test_support as route_support,
)
from tests.unit.web.public_exam_workspace_command_routes_test_support import (
    _BASE,
    _CLIENT_IP,
    FakeAdmitHandler,
    RecordingCommandHandler,
    make_command_app,
    make_registry,
)

admit = route_support.admit
command_handler = route_support.command_handler
registry = route_support.registry
client = route_support.client


@pytest.fixture
def app(
    registry: CuratedAppRegistryProtocol,
    admit: FakeAdmitHandler,
    command_handler: RecordingCommandHandler,
) -> FastAPI:
    return make_command_app(registry=registry, admit=admit, commands=command_handler)


async def test_limits_return_the_configured_max_exam_bytes(client, admit: FakeAdmitHandler) -> None:
    response = await client.get(f"{_BASE}/limits")

    assert response.status_code == 200
    assert response.json() == {"max_exam_bytes": Settings().VAULT_MAX_FILE_BYTES}
    assert admit.calls == [(PublicRequestBucket.GUEST_EDIT, _CLIENT_IP)]
    assert response.headers.get("set-cookie") is None


async def test_limits_read_the_value_from_the_injected_settings(
    admit: FakeAdmitHandler,
    command_handler: RecordingCommandHandler,
) -> None:
    app = make_command_app(
        registry=make_registry(),
        admit=admit,
        commands=command_handler,
        settings=Settings(VAULT_MAX_FILE_BYTES=7_000_000),
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as configured:
        response = await configured.get(f"{_BASE}/limits")

    assert response.status_code == 200
    assert response.json() == {"max_exam_bytes": 7_000_000}


async def test_limits_refuse_an_inactive_runtime_before_admission(
    admit: FakeAdmitHandler, command_handler: RecordingCommandHandler
) -> None:
    app = make_command_app(
        registry=make_registry(runtime_status=CuratedAppPublicRuntimeStatus.CONTRACT_ONLY),
        admit=admit,
        commands=command_handler,
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as inactive:
        response = await inactive.get(f"{_BASE}/limits")

    assert response.status_code == 404
    assert admit.calls == []
