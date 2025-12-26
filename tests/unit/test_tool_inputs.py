import pytest

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.scripting.tool_inputs import (
    ToolInputEnumField,
    ToolInputEnumOption,
    ToolInputField,
    ToolInputFileField,
    ToolInputIntegerField,
    ToolInputStringField,
    normalize_tool_input_schema,
    normalize_tool_input_values,
    validate_input_files_count,
)


def test_normalize_tool_input_schema_with_duplicate_names_raises_validation_error() -> None:
    schema: list[ToolInputField] = [
        ToolInputStringField(name="title", label="Title"),
        ToolInputStringField(name="title", label="Title 2"),
    ]

    with pytest.raises(DomainError) as exc_info:
        normalize_tool_input_schema(input_schema=schema)

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert exc_info.value.details["duplicates"] == ["title"]


def test_normalize_tool_input_schema_with_multiple_file_fields_raises_validation_error() -> None:
    schema: list[ToolInputField] = [
        ToolInputFileField(name="a", label="A", min=0, max=1),
        ToolInputFileField(name="b", label="B", min=0, max=1),
    ]

    with pytest.raises(DomainError) as exc_info:
        normalize_tool_input_schema(input_schema=schema)

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR


def test_validate_input_files_count_when_no_file_field_rejects_any_files() -> None:
    schema: list[ToolInputField] = [ToolInputStringField(name="title", label="Title")]

    with pytest.raises(DomainError) as exc_info:
        validate_input_files_count(input_schema=schema, files_count=1)

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR


def test_validate_input_files_count_enforces_min_max() -> None:
    schema: list[ToolInputField] = [
        ToolInputFileField(name="documents", label="Documents", min=1, max=3)
    ]

    with pytest.raises(DomainError):
        validate_input_files_count(input_schema=schema, files_count=0)

    validate_input_files_count(input_schema=schema, files_count=2)

    with pytest.raises(DomainError):
        validate_input_files_count(input_schema=schema, files_count=4)


def test_normalize_tool_input_values_rejects_unknown_keys() -> None:
    schema: list[ToolInputField] = [ToolInputStringField(name="title", label="Title")]

    with pytest.raises(DomainError) as exc_info:
        normalize_tool_input_values(input_schema=schema, values={"unknown": "x"})

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert exc_info.value.details["unknown_keys"] == ["unknown"]


def test_normalize_tool_input_values_rejects_file_field_name_in_inputs_json() -> None:
    schema: list[ToolInputField] = [
        ToolInputFileField(name="documents", label="Documents", min=0, max=1)
    ]

    with pytest.raises(DomainError) as exc_info:
        normalize_tool_input_values(input_schema=schema, values={"documents": "oops"})

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR


def test_normalize_tool_input_values_drops_empty_strings_and_coerces_integer() -> None:
    schema: list[ToolInputField] = [
        ToolInputStringField(name="title", label="Title"),
        ToolInputIntegerField(name="count", label="Count"),
        ToolInputEnumField(
            name="format",
            label="Format",
            options=[ToolInputEnumOption(value="pdf", label="PDF")],
        ),
    ]

    normalized = normalize_tool_input_values(
        input_schema=schema,
        values={
            "title": "  Hello  ",
            "count": " 2 ",
            "format": "pdf",
        },
    )

    assert normalized == {"title": "Hello", "count": 2, "format": "pdf"}
