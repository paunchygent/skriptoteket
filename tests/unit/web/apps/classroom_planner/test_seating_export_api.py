"""Unit coverage for the classroom-planner seating export API contract."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from skriptoteket.application.curated_apps.classroom_planner import (
    PrepareSeatingExportHandler,
    SeatingExportKind,
    SeatingExportLayoutId,
)
from skriptoteket.application.curated_apps.classroom_planner.exports import (
    PosterSceneFixture,
    PosterSceneFixtureKind,
    PosterSceneFixturePlacement,
    PosterSceneRoom,
    PosterSceneSeat,
    PreparedSeatingExportContract,
    SeatingPosterScene,
)
from skriptoteket.web.api.v1 import apps_classroom_planner_seating as api
from skriptoteket.web.api.v1.apps_classroom_planner_export_contracts import (
    PrepareSeatingExportRequest,
)
from tests.fixtures.identity_fixtures import make_user


def _unwrap_dishka(fn):
    """Extract the original function from Dishka-wrapped handlers."""

    return getattr(fn, "__dishka_orig_func__", fn)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_prepare_seating_export_calls_handler_with_explicit_draft_id():
    user = make_user()
    draft_id = uuid4()
    roster_id = uuid4()
    template_id = uuid4()
    handler = AsyncMock(spec=PrepareSeatingExportHandler)
    handler.handle.return_value = PreparedSeatingExportContract(
        seating_draft_id=draft_id,
        roster_id=roster_id,
        roster_name="Klass 7A",
        template_id=template_id,
        template_name="Sal A",
        export_kind=SeatingExportKind.PDF,
        layout_id=SeatingExportLayoutId.PRETTY_BRUTALIST_POSTER,
        poster_scene=SeatingPosterScene(
            room=PosterSceneRoom(grid_cols=14, grid_rows=9),
            seats=[
                PosterSceneSeat(
                    seat_id="seat-1",
                    x=1,
                    y=2,
                    student_id="student-1",
                    label="Alice A.",
                )
            ],
            fixtures=[
                PosterSceneFixture(
                    fixture_id="fixture-1",
                    source_fixture_ids=("fixture-1",),
                    kind=PosterSceneFixtureKind.WHITEBOARD,
                    x=2,
                    y=0,
                    width=4,
                    height=1,
                    placement=PosterSceneFixturePlacement.WALL,
                    label="Whiteboard",
                )
            ],
        ),
    )

    result = await _unwrap_dishka(api.prepare_seating_export)(
        draft_id=draft_id,
        request=PrepareSeatingExportRequest(
            export_kind=SeatingExportKind.PDF,
            layout_id=SeatingExportLayoutId.PRETTY_BRUTALIST_POSTER,
        ),
        handler=handler,
        user=user,
    )

    assert result.seating_draft_id == draft_id
    assert result.export_kind == SeatingExportKind.PDF
    assert result.poster_scene.seats[0].label == "Alice A."
    handler.handle.assert_awaited_once_with(
        draft_id=draft_id,
        owner_user_id=user.id,
        export_kind=SeatingExportKind.PDF,
        layout_id=SeatingExportLayoutId.PRETTY_BRUTALIST_POSTER,
    )


@pytest.mark.unit
def test_prepare_seating_export_request_rejects_unknown_layout():
    with pytest.raises(ValidationError):
        PrepareSeatingExportRequest(
            export_kind=SeatingExportKind.PDF,
            layout_id="invalid-layout",
        )


@pytest.mark.unit
def test_prepare_seating_export_request_rejects_unknown_export_kind():
    with pytest.raises(ValidationError):
        PrepareSeatingExportRequest(
            export_kind="xlsx",
            layout_id=SeatingExportLayoutId.PRETTY_BRUTALIST_POSTER,
        )
