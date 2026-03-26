"""Contract tests for classroom planner draft DTO serialization."""

from datetime import datetime, timezone
from uuid import uuid4

import pytest

from skriptoteket.domain.curated_apps.classroom_planner.models import PlanDraft, PlanDraftKind
from skriptoteket.web.api.v1.apps_classroom_planner_draft_contracts import serialize_plan_draft


@pytest.mark.unit
def test_serialize_plan_draft_includes_reset_flags() -> None:
    now = datetime.now(timezone.utc)
    draft = PlanDraft(
        id=uuid4(),
        owner_user_id=uuid4(),
        roster_id=uuid4(),
        draft_kind=PlanDraftKind.SEATING,
        template_id=uuid4(),
        smart_enabled=True,
        use_history=True,
        grouping_seating_distance_enabled=True,
        revision=7,
        last_opened_at=now,
        created_at=now,
        updated_at=now,
    )

    result = serialize_plan_draft(draft)

    assert result.smart_enabled is True
    assert result.use_history is True
    assert result.grouping_seating_distance_enabled is True
