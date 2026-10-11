"""Strict Responses JSON schema generated from the producer contract."""

from pydantic import JsonValue

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredOutputSpec,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import DocxBuildEnvelope


def _object(value: JsonValue) -> dict[str, JsonValue]:
    if not isinstance(value, dict):
        raise ValueError("Schema node must be an object.")
    return value


def _strict_schema(value: JsonValue) -> JsonValue:
    """Strict mode requires every property and forbids additional ones."""
    if isinstance(value, list):
        return [_strict_schema(entry) for entry in value]
    if not isinstance(value, dict):
        return value
    result = {
        ("anyOf" if key == "oneOf" else key): _strict_schema(entry)
        for key, entry in value.items()
        if key not in {"default", "discriminator", "title", "properties", "$defs"}
    }
    # Property and definition names are data; only schema keywords are filtered.
    for container in ("properties", "$defs"):
        if container in value:
            result[container] = {
                name: _strict_schema(entry) for name, entry in _object(value[container]).items()
            }
    if result.get("type") == "object":
        result["additionalProperties"] = False
        result["required"] = list(_object(result.get("properties", {})))
    return result


def docx_build_output_spec() -> StructuredOutputSpec:
    return StructuredOutputSpec(
        schema_name="docx_exam_build",
        schema_version="docx_exam_build_v8",
        json_schema=_object(_strict_schema(DocxBuildEnvelope.model_json_schema())),
    )
