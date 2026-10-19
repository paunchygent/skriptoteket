"""Stateless public guest command routes: blank, structure commands, change type and catalog.

These tests run the real FastAPI router and the real domain command functions,
with a fake database admission handler and the real deterministic misspellings
handler. Every structure command's result is compared against a direct call to
the same domain function the signed-in workspace uses.
"""

from __future__ import annotations

import random
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI

from skriptoteket.application.curated_apps.exam_workspace_misspellings import (
    ExamWorkspaceMisspellingsRequest,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_courses import (
    exam_course_catalog_without_profile,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_misspellings import (
    GenerateExamWorkspaceMisspellingsHandler,
)
from skriptoteket.domain.curated_apps.exam_workspace import (
    native_exam_parent_commands as commands,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_course_catalog import (
    load_exam_course_catalog,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_change_type import (
    change_item_type,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
    NativeExamDocumentOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
)
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.public_request_limits import PublicRequestBucket
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_free_text_item,
    make_paragraph,
    make_single_choice_item,
)
from tests.unit.web import (
    public_exam_workspace_command_routes_test_support as route_support,
)
from tests.unit.web.public_exam_workspace_command_routes_test_support import (
    _BASE,
    _CLIENT_IP,
    FakeAdmitHandler,
    RecordingCommandHandler,
    _body,
    _parented_document,
    _response_document,
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


async def test_blank_returns_a_valid_single_question_document(
    client: httpx.AsyncClient, admit: FakeAdmitHandler
) -> None:
    response = await client.post(f"{_BASE}/blank")

    assert response.status_code == 200
    document = _response_document(response)
    assert len(document.items) == 1
    item = document.items[0]
    assert item.item_id == "item_001"
    assert item.sequence == 1
    assert item.kind is NativeExamItemKind.FREE_TEXT
    assert item.points == 1
    assert document.title == ""
    assert document.revision == 1
    assert document.header.course is None
    assert response.json()["export_blockers"] == [
        {"item_id": None, "reason": "title_without_text"},
        {"item_id": "item_001", "reason": "empty_question_text"},
    ]
    assert admit.calls == [(PublicRequestBucket.GUEST_EDIT, _CLIENT_IP)]
    assert response.headers.get("set-cookie") is None


async def test_create_parent_matches_the_domain_function(
    client: httpx.AsyncClient, admit: FakeAdmitHandler
) -> None:
    document = _parented_document()
    expected = commands.create_parent(
        document,
        instruction=(make_paragraph("Del A"),),
        child=make_free_text_item(),
        position=1,
    )

    response = await client.post(
        f"{_BASE}/parents",
        json=_body(
            document,
            instruction=(make_paragraph("Del A"),),
            child=make_free_text_item(),
            position=1,
        ),
    )

    assert response.status_code == 200
    assert _response_document(response) == expected


async def test_add_child_matches_the_domain_function(client: httpx.AsyncClient) -> None:
    document = _parented_document()
    expected = commands.add_child(
        document, parent_id="parent_001", child=make_free_text_item(), position=0
    )

    response = await client.post(
        f"{_BASE}/parents/parent_001/children",
        json=_body(document, child=make_free_text_item(), position=0),
    )

    assert response.status_code == 200
    assert _response_document(response) == expected


async def test_delete_child_matches_the_domain_function(client: httpx.AsyncClient) -> None:
    document = _parented_document()
    expected = commands.delete_child(document, parent_id="parent_001", item_id="item_002")

    response = await client.post(
        f"{_BASE}/parents/parent_001/children/item_002/delete",
        json=_body(document),
    )

    assert response.status_code == 200
    assert response.json()["removed_parent_id"] is None
    assert _response_document(response) == expected


async def test_reorder_children_matches_the_domain_function(client: httpx.AsyncClient) -> None:
    document = _parented_document()
    expected = commands.reorder_children(
        document, parent_id="parent_001", item_ids=("item_003", "item_002")
    )

    response = await client.post(
        f"{_BASE}/parents/parent_001/children/order",
        json=_body(document, item_ids=("item_003", "item_002")),
    )

    assert response.status_code == 200
    assert _response_document(response) == expected


async def test_group_items_matches_the_domain_function(
    client: httpx.AsyncClient, admit: FakeAdmitHandler
) -> None:
    document = _parented_document()
    expected, created_parent_id = commands.group_items(document, item_ids=("item_001",))

    response = await client.post(
        f"{_BASE}/parents/group",
        json=_body(document, item_ids=("item_001",)),
    )

    assert response.status_code == 200
    assert response.json()["created_parent_id"] == created_parent_id
    assert _response_document(response) == expected
    assert admit.calls == [(PublicRequestBucket.GUEST_EDIT, _CLIENT_IP)]
    assert response.headers.get("set-cookie") is None


async def test_create_empty_part_matches_the_domain_function(
    client: httpx.AsyncClient, admit: FakeAdmitHandler
) -> None:
    document = _parented_document()
    expected, created_parent_id = commands.create_empty_part(document, position=1)

    response = await client.post(f"{_BASE}/parents/empty", json=_body(document, position=1))

    assert response.status_code == 200
    assert created_parent_id == "parent_002"
    assert response.json()["created_parent_id"] == created_parent_id
    assert _response_document(response) == expected
    assert admit.calls == [(PublicRequestBucket.GUEST_EDIT, _CLIENT_IP)]
    assert response.headers.get("set-cookie") is None


async def test_move_item_into_a_part_matches_the_domain_function(
    client: httpx.AsyncClient,
) -> None:
    document = _parented_document()
    expected = commands.move_item(document, item_id="item_001", target_parent_id="parent_001")

    response = await client.post(
        f"{_BASE}/parents/move",
        json=_body(document, item_id="item_001", target_parent_id="parent_001"),
    )

    assert response.status_code == 200
    assert _response_document(response) == expected


async def test_move_item_to_standalone_matches_the_domain_function(
    client: httpx.AsyncClient,
) -> None:
    document = _parented_document()
    expected = commands.move_item(document, item_id="item_002", target_parent_id=None)

    response = await client.post(
        f"{_BASE}/parents/move",
        json=_body(document, item_id="item_002", target_parent_id=None),
    )

    assert response.status_code == 200
    assert _response_document(response) == expected
    assert response.headers.get("set-cookie") is None


@pytest.mark.parametrize("mode", ["keep_questions", "with_questions"])
async def test_delete_parent_matches_the_domain_function(
    client: httpx.AsyncClient, mode: str
) -> None:
    document = _parented_document()
    delete = (
        commands.delete_parent_with_children if mode == "with_questions" else commands.delete_parent
    )
    expected = delete(document, parent_id="parent_001")

    response = await client.post(
        f"{_BASE}/parents/parent_001/delete",
        json=_body(document, mode=mode),
    )

    assert response.status_code == 200
    assert response.json()["removed_parent_id"] == "parent_001"
    assert _response_document(response) == expected


async def test_change_type_matches_the_domain_function(client: httpx.AsyncClient) -> None:
    document = _parented_document()
    expected = change_item_type(
        document,
        item_id="item_001",
        target_kind=NativeExamItemKind.SINGLE_CHOICE,
        rng=random.Random(1),
    )

    response = await client.post(
        f"{_BASE}/change-type",
        json=_body(document, item_id="item_001", target_kind="single_choice"),
    )

    assert response.status_code == 200
    assert response.json()["dropped_content"] == list(expected.dropped_content)
    assert _response_document(response) == expected.document


async def test_change_type_returns_dropped_content(client: httpx.AsyncClient) -> None:
    document = NativeExamDocument(
        document_id=uuid4(),
        revision=1,
        title="Omprov: grammatik",
        items=(make_single_choice_item(),),
        origin=NativeExamDocumentOrigin(kind="created"),
    )

    response = await client.post(
        f"{_BASE}/change-type",
        json=_body(document, item_id="item_001", target_kind="gap_fill"),
    )

    assert response.status_code == 200
    assert response.json()["dropped_content"] == ["choices", "correct_choice_ids"]


async def test_misspellings_match_the_signed_in_handler(client: httpx.AsyncClient) -> None:
    request = ExamWorkspaceMisspellingsRequest(
        accepted_values=("NF", "Nf"),
        other_gold_answers=("NF-variant",),
        document_text="Skriv namnet på staden.",
    )

    response = await client.post(
        f"{_BASE}/answer-misspellings",
        json=request.model_dump(mode="json"),
    )

    assert response.status_code == 200
    expected = GenerateExamWorkspaceMisspellingsHandler().handle(request=request)
    assert response.json()["automatic_values"] == list(expected.automatic_values)


async def test_courses_need_no_user_and_keep_the_default_order(
    client: httpx.AsyncClient, admit: FakeAdmitHandler
) -> None:
    response = await client.get(f"{_BASE}/courses")

    assert response.status_code == 200
    expected = exam_course_catalog_without_profile()
    assert response.json()["registered_course_keys"] == []
    assert response.json()["courses"] == [
        course.model_dump(mode="json") for course in expected.courses
    ]
    assert response.json()["generated_at"] == load_exam_course_catalog().generated_at
    assert admit.calls == [(PublicRequestBucket.GUEST_EDIT, _CLIENT_IP)]


async def test_unused_catalog_path_has_no_profile_lookup(
    client: httpx.AsyncClient,
) -> None:
    """The guest catalog is the committed snapshot in file order, with no user anywhere."""

    response = await client.get(f"{_BASE}/courses")

    catalog = load_exam_course_catalog()
    assert response.json()["courses"] == [
        course.model_dump(mode="json") for course in catalog.courses
    ]
