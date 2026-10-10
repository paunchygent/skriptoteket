"""Typed strict JSON schema generation and required-field admission."""

import json

from pydantic import JsonValue

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredOutputSpec,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
    DocxBuildEntry,
    DocxBuildEnvelope,
)


def _object(value: JsonValue) -> dict[str, JsonValue]:
    if not isinstance(value, dict):
        raise ValueError("Svaret följer inte JSON-schemat.")
    return value


def _strict_schema(value: JsonValue) -> JsonValue:
    if isinstance(value, list):
        return [_strict_schema(entry) for entry in value]
    if not isinstance(value, dict):
        return value
    result = {
        ("anyOf" if key == "oneOf" else key): _strict_schema(entry)
        for key, entry in value.items()
        if key not in {"default", "discriminator"}
    }
    if result.get("type") == "object":
        result["additionalProperties"] = False
        result["required"] = list(_object(result.get("properties", {})))
    return result


def docx_build_output_spec() -> StructuredOutputSpec:
    return StructuredOutputSpec(
        schema_name="docx_exam_build",
        schema_version="docx_exam_build_v1",
        json_schema=_object(_strict_schema(DocxBuildEnvelope.model_json_schema())),
    )


def _require_union(
    value: JsonValue, branches: JsonValue, definitions: dict[str, JsonValue]
) -> None:
    if not isinstance(branches, list):
        raise ValueError("Ogiltigt unionsschema.")
    for branch in branches:
        try:
            _required_shape(value, _object(branch), definitions)
            return
        except ValueError:
            continue
    raise ValueError("Svaret följer inte JSON-schemat.")


def _require_scalar(value: JsonValue, schema: dict[str, JsonValue]) -> None:
    kind = schema.get("type")
    valid_type = {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "null": value is None,
        "integer": type(value) is int,
        "number": type(value) in {int, float},
        "boolean": type(value) is bool,
    }
    if isinstance(kind, str) and kind in valid_type and not valid_type[kind]:
        raise ValueError("Svaret följer inte JSON-schemat.")
    if "const" in schema and value != schema["const"]:
        raise ValueError("Svaret följer inte JSON-schemat.")
    enumeration = schema.get("enum")
    if isinstance(enumeration, list) and value not in enumeration:
        raise ValueError("Svaret följer inte JSON-schemat.")


def _required_shape(
    value: JsonValue, schema: dict[str, JsonValue], definitions: dict[str, JsonValue]
) -> None:
    """Enforce API-required fields, including native fields with Python defaults."""
    reference = schema.get("$ref")
    if isinstance(reference, str):
        _required_shape(value, _object(definitions[reference.rsplit("/", 1)[1]]), definitions)
        return
    if "anyOf" in schema:
        _require_union(value, schema["anyOf"], definitions)
        return
    _require_scalar(value, schema)
    if schema.get("type") == "object":
        properties = _object(schema["properties"])
        fields = _object(value)
        if set(fields) != set(properties):
            raise ValueError("Svaret saknar fält eller innehåller okända fält.")
        for key, child in properties.items():
            _required_shape(fields[key], _object(child), definitions)
    elif schema.get("type") == "array" and isinstance(value, list):
        for child in value:
            _required_shape(child, _object(schema["items"]), definitions)


def parse_build_entry(value: JsonValue) -> DocxBuildEntry:
    schema = docx_build_output_spec().json_schema
    definitions = _object(schema["$defs"])
    _required_shape(value, {"$ref": "#/$defs/DocxBuildEntry"}, definitions)
    return DocxBuildEntry.model_validate_json(json.dumps(value), strict=True)
