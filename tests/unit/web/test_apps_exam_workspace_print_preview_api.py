"""Access control, delegation and wire shape of the print preview route (W5).

The route is called directly: FastAPI registration returns the route function
unchanged, so mypy checks every argument below against the production route
signature and the handler protocol it declares.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from skriptoteket.application.curated_apps.exam_workspace import (
    ExamWorkspacePrintPreviewResponse,
)
from skriptoteket.domain.errors import DomainError
from skriptoteket.domain.identity.models import User
from skriptoteket.web.api.v1 import apps_conversion_hub_exam_workspace as api
from tests.fixtures.identity_fixtures import make_user
from tests.unit.web.test_apps_exam_workspace_answer_key_suggestions_api import FakeRegistry

pytestmark = pytest.mark.unit


class CapturingPreviewHandler:
    """A handler double satisfying `PreviewExamWorkspacePrintHandlerProtocol`."""

    def __init__(self, response: ExamWorkspacePrintPreviewResponse) -> None:
        self.response = response
        self.calls: list[tuple[UUID, UUID, int]] = []

    async def handle(
        self, *, actor: User, lineage_id: UUID, expected_revision: int
    ) -> ExamWorkspacePrintPreviewResponse:
        self.calls.append((actor.id, lineage_id, expected_revision))
        return self.response


def _response() -> ExamWorkspacePrintPreviewResponse:
    return ExamWorkspacePrintPreviewResponse(
        revision=2,
        status="ready",
        pages=["data:image/png;base64,AAAA", "data:image/png;base64,BBBB"],
        question_pages={"item_001": 0, "item_002": 1},
        message=None,
    )


@pytest.mark.asyncio
async def test_route_delegates_the_saved_head_preview() -> None:
    response = _response()
    handler = CapturingPreviewHandler(response)
    lineage_id = uuid4()
    user = make_user()

    result = await api.preview_exam_workspace_document_print(
        lineage_id=lineage_id,
        expected_revision=2,
        registry=FakeRegistry(),
        handler=handler,
        user=user,
    )

    assert result is response
    assert handler.calls == [(user.id, lineage_id, 2)]


@pytest.mark.asyncio
async def test_route_json_carries_pages_question_pages_and_status() -> None:
    handler = CapturingPreviewHandler(_response())

    result = await api.preview_exam_workspace_document_print(
        lineage_id=uuid4(),
        expected_revision=2,
        registry=FakeRegistry(),
        handler=handler,
        user=make_user(),
    )

    assert result.model_dump(mode="json") == {
        "revision": 2,
        "status": "ready",
        "pages": ["data:image/png;base64,AAAA", "data:image/png;base64,BBBB"],
        "question_pages": {"item_001": 0, "item_002": 1},
        "message": None,
    }


@pytest.mark.asyncio
async def test_route_checks_app_access_before_the_preview() -> None:
    class MissingAppRegistry(FakeRegistry):
        def get_by_app_id(self, *, app_id: str) -> None:
            return None

    handler = CapturingPreviewHandler(_response())

    with pytest.raises(DomainError):
        await api.preview_exam_workspace_document_print(
            lineage_id=uuid4(),
            expected_revision=2,
            registry=MissingAppRegistry(),
            handler=handler,
            user=make_user(),
        )

    assert handler.calls == []
