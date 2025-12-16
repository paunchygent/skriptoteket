from __future__ import annotations

import pytest

from skriptoteket.domain.errors import DomainError, ErrorCode, not_found
from skriptoteket.domain.scripting.models import RunContext, RunStatus, VersionState
from skriptoteket.web.ui_text import (
    run_context_label,
    run_status_label,
    ui_error_message,
    version_state_label,
)


@pytest.mark.unit
def test_labels_map_known_values() -> None:
    assert version_state_label(VersionState.DRAFT) == "Utkast"
    assert run_status_label(RunStatus.SUCCEEDED) == "Lyckades"
    assert run_context_label(RunContext.SANDBOX) == "Testläge"


@pytest.mark.unit
def test_labels_fall_back_to_input_for_unknown_values() -> None:
    assert version_state_label("mystery") == "mystery"
    assert run_status_label("mystery") == "mystery"
    assert run_context_label("mystery") == "mystery"


@pytest.mark.unit
def test_ui_error_message_forbidden() -> None:
    exc = DomainError(code=ErrorCode.FORBIDDEN, message="no", details={})
    assert ui_error_message(exc) == "Du saknar behörighet för detta."


@pytest.mark.unit
@pytest.mark.parametrize(
    ("resource", "expected"),
    [
        ("Tool", "Verktyget hittades inte."),
        ("ToolVersion", "Versionen hittades inte."),
        ("ToolRun", "Körningen hittades inte."),
        ("Artifact", "Filen hittades inte."),
        ("ArtifactFile", "Filen hittades inte."),
        ("Other", "Hittades inte."),
    ],
)
def test_ui_error_message_not_found_resource_specific(resource: str, expected: str) -> None:
    exc = not_found(resource, "123")
    assert ui_error_message(exc) == expected


@pytest.mark.unit
def test_ui_error_message_conflict_stale_head() -> None:
    exc = DomainError(
        code=ErrorCode.CONFLICT,
        message="stale",
        details={"current_head_version_id": "abc"},
    )
    assert (
        ui_error_message(exc)
        == "Utkastet har ändrats sedan du öppnade sidan. Ladda om och försök igen."
    )


@pytest.mark.unit
def test_ui_error_message_validation_expected_parent() -> None:
    exc = DomainError(
        code=ErrorCode.VALIDATION_ERROR,
        message="invalid",
        details={"expected_parent_version_id": "abc"},
    )
    assert ui_error_message(exc) == "Versionen stämmer inte längre. Ladda om och försök igen."


@pytest.mark.unit
@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("Title is required", "Titel krävs."),
        ("Title must be 255 characters or less", "Titeln får vara högst 255 tecken."),
        ("Other", "Ogiltig indata."),
    ],
)
def test_ui_error_message_validation_title_messages(message: str, expected: str) -> None:
    exc = DomainError(code=ErrorCode.VALIDATION_ERROR, message=message, details={})
    assert ui_error_message(exc) == expected


@pytest.mark.unit
def test_ui_error_message_service_unavailable() -> None:
    exc = DomainError(code=ErrorCode.SERVICE_UNAVAILABLE, message="down", details={})
    assert ui_error_message(exc) == "Tjänsten är tillfälligt otillgänglig. Försök igen."


@pytest.mark.unit
def test_ui_error_message_default() -> None:
    exc = DomainError(code=ErrorCode.INTERNAL_ERROR, message="boom", details={})
    assert ui_error_message(exc) == "Ett oväntat fel inträffade."
