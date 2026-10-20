"""Access control, delegation and wire shape of the Exam.net export checklist route (Q15).

The route is called directly: FastAPI registration returns the route function
unchanged, so mypy checks every argument below against the production route
signature and the handler protocol it declares.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from skriptoteket.application.curated_apps.exam_workspace import (
    ExamWorkspaceExportChecklistResponse,
    ExamWorkspaceExportChecklistRoundedGaps,
    ExamWorkspaceExportFile,
    ExamWorkspaceExportTarget,
)
from skriptoteket.domain.errors import DomainError
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.vault import VaultFile
from skriptoteket.web.api.v1 import apps_conversion_hub_exam_workspace_exports as api
from tests.fixtures.identity_fixtures import make_user
from tests.unit.web.test_apps_exam_workspace_answer_key_suggestions_api import FakeRegistry

pytestmark = pytest.mark.unit


class CapturingChecklistHandler:
    """A handler double satisfying `ExportExamWorkspaceDocumentHandlerProtocol`."""

    def __init__(self, response: ExamWorkspaceExportChecklistResponse) -> None:
        self.response = response
        self.checklist_calls: list[tuple[UUID, UUID, int]] = []
        self.export_calls: list[tuple[UUID, UUID, ExamWorkspaceExportTarget]] = []

    async def handle(
        self,
        *,
        actor: User,
        lineage_id: UUID,
        target: ExamWorkspaceExportTarget,
        expected_revision: int,
    ) -> ExamWorkspaceExportFile:
        self.export_calls.append((actor.id, lineage_id, target))
        raise AssertionError("the checklist route must not run an export")

    async def save(
        self,
        *,
        actor: User,
        lineage_id: UUID,
        target: ExamWorkspaceExportTarget,
        expected_revision: int,
    ) -> VaultFile:
        self.export_calls.append((actor.id, lineage_id, target))
        raise AssertionError("the checklist route must not save an export")

    async def checklist(
        self, *, actor: User, lineage_id: UUID, expected_revision: int
    ) -> ExamWorkspaceExportChecklistResponse:
        self.checklist_calls.append((actor.id, lineage_id, expected_revision))
        return self.response


def _rounded_entry() -> ExamWorkspaceExportChecklistRoundedGaps:
    return ExamWorkspaceExportChecklistRoundedGaps(
        kind="rounded_gaps",
        item_id="item_005",
        question_text="Gör satsdelsanalys av meningarna.",
        points=6,
        gap_points=0.42,
    )


@pytest.mark.asyncio
async def test_route_delegates_the_head_document_checklist() -> None:
    entry = _rounded_entry()
    handler = CapturingChecklistHandler(
        ExamWorkspaceExportChecklistResponse(entries=(entry,), inline_choice_min_options=2)
    )
    lineage_id = uuid4()
    user = make_user()

    response = await api.export_exam_workspace_document_checklist(
        lineage_id=lineage_id,
        expected_revision=2,
        registry=FakeRegistry(),
        handler=handler,
        user=user,
    )

    assert response.entries == (entry,)
    assert handler.checklist_calls == [(user.id, lineage_id, 2)]
    assert handler.export_calls == []


@pytest.mark.asyncio
async def test_route_json_carries_the_required_kind_discriminator() -> None:
    entry = _rounded_entry()
    handler = CapturingChecklistHandler(
        ExamWorkspaceExportChecklistResponse(entries=(entry,), inline_choice_min_options=2)
    )

    response = await api.export_exam_workspace_document_checklist(
        lineage_id=uuid4(),
        expected_revision=2,
        registry=FakeRegistry(),
        handler=handler,
        user=make_user(),
    )

    assert response.model_dump(mode="json") == {
        "entries": [
            {
                "kind": "rounded_gaps",
                "item_id": "item_005",
                "question_text": "Gör satsdelsanalys av meningarna.",
                "points": 6,
                "gap_points": 0.42,
            }
        ],
        "inline_choice_min_options": 2,
    }


@pytest.mark.asyncio
async def test_route_checks_app_access_before_the_checklist() -> None:
    class MissingAppRegistry(FakeRegistry):
        def get_by_app_id(self, *, app_id: str) -> None:
            return None

    handler = CapturingChecklistHandler(
        ExamWorkspaceExportChecklistResponse(entries=(), inline_choice_min_options=2)
    )

    with pytest.raises(DomainError):
        await api.export_exam_workspace_document_checklist(
            lineage_id=uuid4(),
            expected_revision=2,
            registry=MissingAppRegistry(),
            handler=handler,
            user=make_user(),
        )

    assert handler.checklist_calls == []
