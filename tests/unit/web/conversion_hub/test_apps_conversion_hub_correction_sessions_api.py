"""Unit coverage for Exam Converter correction-session API routes.

Purpose:
  Prove PR-0334 route functions expose read, replacement, and revert contracts while
  staying thin over application handlers and Conversion Hub access checks.

Relationships:
  - Covers `web.api.v1.apps_conversion_hub_correction_sessions`.
  - Complements application handler tests for owner scope and conflicts.
"""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.exam_converter_correction_sessions import (
    ExamConverterCorrectionIntentWrite,
    ExamConverterCorrectionSessionResponse,
    ReplaceExamConverterCorrectionIntentsRequest,
    RevertExamConverterCorrectionIntentRequest,
)
from skriptoteket.domain.curated_apps.exam_converter_correction_sessions import (
    ExamConverterCorrectionSourceBinding,
    ExamConverterCorrectionTarget,
)
from skriptoteket.domain.identity.models import Role
from skriptoteket.web.api.v1 import apps_conversion_hub_correction_sessions as api
from tests.fixtures.identity_fixtures import make_user


def _unwrap_dishka(fn):
    return getattr(fn, "__dishka_orig_func__", fn)


class FakeRegistry:
    def get_by_app_id(self, *, app_id: str):
        return SimpleNamespace(app_id=app_id, min_role=Role.USER)


class CapturingHandler:
    def __init__(self, result: ExamConverterCorrectionSessionResponse) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    async def handle(self, **kwargs) -> ExamConverterCorrectionSessionResponse:
        self.calls.append(kwargs)
        return self.result


def _binding() -> ExamConverterCorrectionSourceBinding:
    return ExamConverterCorrectionSourceBinding(
        source_authoring_schema_version="exam_authoring_ir_v1",
        source_bundle_id="bundle-001",
        source_file_sha256="sha256:source-file",
        source_state_sha256="sha256:source-state",
        source_state_signature="signed-source-state",
    )


def _intent() -> ExamConverterCorrectionIntentWrite:
    return ExamConverterCorrectionIntentWrite(
        entry_id="entry-point-item-001",
        source_binding=_binding(),
        item_id="item-001",
        sequence=1,
        item_type="multiple_choice",
        source_item_fingerprint="sha256:item-001",
        kind="point_correction",
        target=ExamConverterCorrectionTarget(),
        payload={"kind": "point_correction", "max_score": 2},
    )


def _response() -> ExamConverterCorrectionSessionResponse:
    owner_id = uuid4()
    job_id = uuid4()
    return ExamConverterCorrectionSessionResponse.empty(
        owner_user_id=owner_id,
        conversion_hub_job_id=job_id,
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_correction_session_delegates_to_handler() -> None:
    user = make_user()
    job_id = uuid4()
    handler = CapturingHandler(_response())

    result = await _unwrap_dishka(api.get_exam_converter_correction_session)(
        job_id=job_id,
        registry=FakeRegistry(),
        handler=handler,
        user=user,
    )

    assert result.session_version == 0
    assert handler.calls[0]["actor"] == user
    assert handler.calls[0]["job_id"] == job_id


@pytest.mark.unit
@pytest.mark.asyncio
async def test_replace_correction_intents_delegates_plural_request() -> None:
    user = make_user()
    job_id = uuid4()
    request = ReplaceExamConverterCorrectionIntentsRequest(
        expected_session_version=0,
        intents=[_intent()],
    )
    handler = CapturingHandler(_response())

    await _unwrap_dishka(api.replace_exam_converter_correction_intents)(
        job_id=job_id,
        request=request,
        registry=FakeRegistry(),
        handler=handler,
        user=user,
    )

    assert handler.calls[0]["request"] == request


@pytest.mark.unit
@pytest.mark.asyncio
async def test_revert_correction_intent_exposes_delete_contract() -> None:
    user = make_user()
    request = RevertExamConverterCorrectionIntentRequest(
        expected_session_version=1,
        target_key="point_correction:item-001:1:multiple_choice:sha256:item-001",
    )
    handler = CapturingHandler(_response())

    await _unwrap_dishka(api.revert_exam_converter_correction_intent)(
        job_id=uuid4(),
        request=request,
        registry=FakeRegistry(),
        handler=handler,
        user=user,
    )

    assert handler.calls[0]["request"] == request
