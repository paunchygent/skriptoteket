"""Route tests for the admin answer-key lease-status API.

Purpose:
    Prove the operator surface projects the day usage into allocated, spent,
    remaining, and the UTC reset instant, including an untouched (empty) day.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from unittest.mock import AsyncMock

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_token_lease import (
    AnswerKeyTokenLeaseDayUsage,
)
from skriptoteket.domain.identity.models import Role
from skriptoteket.protocols.exam_answer_key import AnswerKeyLeaseStatusHandlerProtocol
from skriptoteket.web.api.v1 import admin_answer_key_lease
from tests.unit.web.admin_scripting_test_support import _original, _user

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_status_projects_the_day_balance_with_the_reset_instant() -> None:
    handler = AsyncMock(spec=AnswerKeyLeaseStatusHandlerProtocol)
    handler.handle.return_value = AnswerKeyTokenLeaseDayUsage(
        utc_day=date(2026, 8, 29),
        daily_token_limit=5_000_000,
        charged_tokens=1_250_000,
    )
    admin = _user(role=Role.ADMIN)

    response = await _original(admin_answer_key_lease.get_answer_key_lease_status)(
        handler=handler,
        user=admin,
    )

    assert response.utc_day == date(2026, 8, 29)
    assert response.allocated_tokens == 5_000_000
    assert response.spent_tokens == 1_250_000
    assert response.available_tokens == 3_750_000
    assert response.resets_at == datetime(2026, 8, 30, 0, 0, tzinfo=UTC)
    handler.handle.assert_awaited_once()
    assert handler.handle.call_args.kwargs["actor"] is admin


@pytest.mark.asyncio
async def test_status_reads_an_untouched_day_as_a_full_allocation() -> None:
    handler = AsyncMock(spec=AnswerKeyLeaseStatusHandlerProtocol)
    handler.handle.return_value = AnswerKeyTokenLeaseDayUsage(
        utc_day=date(2026, 8, 29),
        daily_token_limit=5_000_000,
        charged_tokens=0,
    )

    response = await _original(admin_answer_key_lease.get_answer_key_lease_status)(
        handler=handler,
        user=_user(role=Role.SUPERUSER),
    )

    assert response.spent_tokens == 0
    assert response.available_tokens == 5_000_000
    assert response.resets_at == datetime(2026, 8, 30, 0, 0, tzinfo=UTC)
