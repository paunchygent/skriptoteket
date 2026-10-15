"""Access control and request delegation for teacher-keyed misspellings."""

import pytest
from pydantic import ValidationError

from skriptoteket.application.curated_apps.exam_workspace_misspellings import (
    ExamWorkspaceMisspellingsRequest,
    ExamWorkspaceMisspellingsResponse,
)
from skriptoteket.domain.errors import DomainError
from skriptoteket.web.api.v1 import apps_conversion_hub_exam_workspace as api
from tests.fixtures.identity_fixtures import make_user
from tests.unit.web.test_apps_exam_workspace_answer_key_suggestions_api import FakeRegistry

pytestmark = pytest.mark.unit


class CapturingHandler:
    def __init__(self) -> None:
        self.requests: list[ExamWorkspaceMisspellingsRequest] = []

    def handle(
        self, *, request: ExamWorkspaceMisspellingsRequest
    ) -> ExamWorkspaceMisspellingsResponse:
        self.requests.append(request)
        return ExamWorkspaceMisspellingsResponse(automatic_values=("Stokholm",))


def test_route_delegates_without_changing_document_language_input() -> None:
    request = ExamWorkspaceMisspellingsRequest(
        accepted_values=("Stockholm",),
        other_gold_answers=("Stockholm", "Göteborg"),
        document_text="Vad heter Sveriges huvudstad?",
    )
    handler = CapturingHandler()
    response = api.generate_exam_workspace_misspellings(
        request=request, registry=FakeRegistry(), handler=handler, user=make_user()
    )
    assert response.automatic_values == ("Stokholm",)
    assert handler.requests == [request]


def test_route_checks_app_access_before_generating() -> None:
    class MissingAppRegistry(FakeRegistry):
        def get_by_app_id(self, *, app_id: str) -> None:
            return None

    handler = CapturingHandler()
    request = ExamWorkspaceMisspellingsRequest(
        accepted_values=("Stockholm",), other_gold_answers=(), document_text="Prov"
    )
    with pytest.raises(DomainError):
        api.generate_exam_workspace_misspellings(
            request=request, registry=MissingAppRegistry(), handler=handler, user=make_user()
        )
    assert handler.requests == []


@pytest.mark.parametrize("value", ["", "x" * 201])
def test_request_bounds_values_before_distance_computation(value: str) -> None:
    with pytest.raises(ValidationError):
        ExamWorkspaceMisspellingsRequest(
            accepted_values=(value,), other_gold_answers=(), document_text=""
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("accepted_values", ["word"] * 101),
        ("other_gold_answers", ["word"] * 1001),
        ("document_text", "x" * 1_000_001),
        ("document_text", "å" * 500_001),
    ],
    ids=("added_answers", "gold_answers", "document_ascii_bytes", "document_utf8_bytes"),
)
def test_request_rejects_oversized_payload_without_truncation(field: str, value: object) -> None:
    payload: dict[str, object] = {
        "accepted_values": ["word"],
        "other_gold_answers": [],
        "document_text": "",
    }
    payload[field] = value
    with pytest.raises(ValidationError):
        ExamWorkspaceMisspellingsRequest.model_validate(payload)


def test_request_rejects_unexpected_language_override() -> None:
    with pytest.raises(ValidationError):
        ExamWorkspaceMisspellingsRequest.model_validate(
            {
                "accepted_values": ["Stockholm"],
                "other_gold_answers": [],
                "document_text": "Svenskt prov",
                "language": "en",
            }
        )
