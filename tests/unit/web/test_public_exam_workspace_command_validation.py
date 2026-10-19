"""Public guest command validation: domain refusals and unknown body fields.

These tests run the real FastAPI router and assert the contracted 404/422
shapes when a guest command names something unknown or breaks a domain rule.
"""

from __future__ import annotations

import httpx
import pytest
from fastapi import FastAPI

from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
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
    _single_child_document,
    make_command_app,
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


async def test_deleting_the_last_question_refuses(client: httpx.AsyncClient) -> None:
    document = _single_child_document()

    response = await client.post(
        f"{_BASE}/parents/parent_001/children/item_001/delete",
        json=_body(document),
    )

    assert response.status_code == 422
    assert response.json()["error"]["details"]["reason"] == "exam_requires_question"


async def test_grouping_an_item_already_in_a_part_refuses(client: httpx.AsyncClient) -> None:
    document = _parented_document()

    response = await client.post(
        f"{_BASE}/parents/group",
        json=_body(document, item_ids=("item_002",)),
    )

    assert response.status_code == 422
    assert response.json()["error"]["details"]["reason"] == "item_in_part"


async def test_moving_into_an_unknown_part_refuses(client: httpx.AsyncClient) -> None:
    document = _parented_document()

    response = await client.post(
        f"{_BASE}/parents/move",
        json=_body(document, item_id="item_001", target_parent_id="parent_999"),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NOT_FOUND"


async def test_unknown_extra_field_in_a_body_is_refused(client: httpx.AsyncClient) -> None:
    body = _body(
        _parented_document(),
        instruction=(make_paragraph("Del A"),),
        child=make_free_text_item(),
        position=1,
    )
    body["expected_cursor"] = "5f0e5e5e-0000-0000-0000-000000000000"

    response = await client.post(f"{_BASE}/parents", json=body)

    assert response.status_code == 422


async def test_unknown_extra_field_in_a_part_command_body_is_refused(
    client: httpx.AsyncClient,
) -> None:
    body = _body(_parented_document(), position=0)
    body["expected_cursor"] = "5f0e5e5e-0000-0000-0000-000000000000"

    response = await client.post(f"{_BASE}/parents/empty", json=body)

    assert response.status_code == 422
