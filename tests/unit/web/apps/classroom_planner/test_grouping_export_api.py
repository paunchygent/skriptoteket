"""Unit coverage for the classroom-planner grouping export API contract."""

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from skriptoteket.application.curated_apps.classroom_planner import (
    GroupingExportKind,
    PrepareGroupingExportHandler,
)
from skriptoteket.application.curated_apps.classroom_planner.exports import (
    GroupingExportPresentation,
    GroupingPresentationGroup,
    GroupingPresentationMember,
    PreparedGroupingExportContract,
)
from skriptoteket.web.api.v1 import apps_classroom_planner_grouping as api
from skriptoteket.web.api.v1.apps_classroom_planner_export_contracts import (
    PrepareGroupingExportRequest,
)
from tests.fixtures.identity_fixtures import make_user


def _unwrap_dishka(fn):
    return getattr(fn, "__dishka_orig_func__", fn)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_prepare_grouping_export_calls_handler_with_explicit_draft_id():
    user = make_user()
    draft_id = uuid4()
    handler = AsyncMock(spec=PrepareGroupingExportHandler)
    handler.handle.return_value = PreparedGroupingExportContract(
        grouping_draft_id=draft_id,
        roster_id=uuid4(),
        export_kind=GroupingExportKind.XLSX,
        paper_size=None,
        presentation=GroupingExportPresentation(
            draft_id=draft_id,
            class_name="Klass 7A",
            title="Gruppindelning",
            filename_stem="klass-7a-gruppindelning",
            groups=(
                GroupingPresentationGroup(
                    group_label="Grupp 1",
                    group_order=0,
                    members=(
                        GroupingPresentationMember(
                            member_order=1,
                            display_name="Ada Lovelace",
                        ),
                    ),
                ),
            ),
        ),
    )

    result = await _unwrap_dishka(api.prepare_grouping_export)(
        draft_id=draft_id,
        request=PrepareGroupingExportRequest(
            export_kind=GroupingExportKind.XLSX,
            paper_size=None,
        ),
        handler=handler,
        user=user,
    )

    assert result.draft_id == draft_id
    assert result.export_kind is GroupingExportKind.XLSX
    assert result.presentation.groups[0].members[0].display_name == "Ada Lovelace"
    handler.handle.assert_awaited_once_with(
        draft_id=draft_id,
        owner_user_id=user.id,
        export_kind=GroupingExportKind.XLSX,
        paper_size=None,
    )


@pytest.mark.unit
def test_prepare_grouping_export_request_rejects_unknown_export_kind():
    with pytest.raises(ValidationError):
        PrepareGroupingExportRequest(
            export_kind="invalid-export-kind",
            paper_size=None,
        )


@pytest.mark.unit
def test_prepare_grouping_export_request_rejects_unknown_paper_size():
    with pytest.raises(ValidationError):
        PrepareGroupingExportRequest(
            export_kind=GroupingExportKind.PDF,
            paper_size="a5_portrait",
        )
