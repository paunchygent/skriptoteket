"""Public guest command admission: limiter refusals and the request size cap.

These tests run the real FastAPI router and prove a refused admission returns
429 without running any command, and an oversized body is rejected with 413.
"""

from __future__ import annotations

import random

import httpx
import pytest
from fastapi import FastAPI

from skriptoteket.config import Settings
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.public_request_limits import (
    PublicRequestBucket,
    PublicRequestRefusal,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_free_text_item,
    make_paragraph,
)
from tests.unit.web import (
    public_exam_workspace_command_routes_test_support as route_support,
)
from tests.unit.web.public_exam_workspace_command_routes_test_support import (
    _BASE,
    FakeAdmitHandler,
    RecordingCommandHandler,
    _body,
    _parented_document,
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


@pytest.mark.parametrize(
    "refusal", [PublicRequestRefusal.CALLER_LIMIT, PublicRequestRefusal.POOL_LIMIT]
)
async def test_refused_admission_returns_429_and_never_runs_the_command(
    client: httpx.AsyncClient,
    admit: FakeAdmitHandler,
    command_handler: RecordingCommandHandler,
    refusal: PublicRequestRefusal,
) -> None:
    admit.refusal = refusal

    response = await client.post(
        f"{_BASE}/parents",
        json=_body(
            _parented_document(),
            instruction=(make_paragraph("Del A"),),
            child=make_free_text_item(),
            position=1,
        ),
    )

    assert response.status_code == 429
    assert response.json()["error"]["details"] == {
        "reason": refusal.value,
        "bucket": PublicRequestBucket.GUEST_EDIT.value,
    }
    assert command_handler.create_parent_calls == 0


@pytest.mark.parametrize(
    "refusal", [PublicRequestRefusal.CALLER_LIMIT, PublicRequestRefusal.POOL_LIMIT]
)
async def test_refused_admission_returns_429_and_never_runs_the_part_commands(
    client: httpx.AsyncClient,
    admit: FakeAdmitHandler,
    command_handler: RecordingCommandHandler,
    refusal: PublicRequestRefusal,
) -> None:
    admit.refusal = refusal

    response = await client.post(
        f"{_BASE}/parents/group",
        json=_body(_parented_document(), item_ids=("item_001",)),
    )

    assert response.status_code == 429
    assert response.json()["error"]["details"] == {
        "reason": refusal.value,
        "bucket": PublicRequestBucket.GUEST_EDIT.value,
    }
    assert command_handler.group_items_calls == 0
    assert command_handler.create_empty_part_calls == 0
    assert command_handler.move_item_calls == 0


async def test_oversized_body_is_rejected(admit: FakeAdmitHandler) -> None:
    app = make_command_app(
        registry=make_registry(),
        admit=admit,
        commands=RecordingCommandHandler(rng=random.Random(1)),
        settings=Settings(PUBLIC_GUEST_EXAM_MAX_REQUEST_BYTES=64),
    )
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as limited:
        response = await limited.post(
            f"{_BASE}/parents",
            json=_body(
                _parented_document(),
                instruction=(make_paragraph("Del A"),),
                child=make_free_text_item(),
                position=1,
            ),
        )

    assert response.status_code == 413
    assert response.json()["error"]["details"]["reason"] == "payload_too_large"
