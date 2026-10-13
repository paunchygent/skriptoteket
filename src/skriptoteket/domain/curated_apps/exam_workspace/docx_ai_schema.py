"""Strict Responses JSON schema generated from the producer contract.

Each request narrows the schema to its batch: every anchor field accepts only the batch's
own chunk anchors and an item's kind only the batch's kinds, and a batch without gap_fill
offers no gap segment, so the schema is the only gate on model output.
"""

from collections.abc import Iterable

from pydantic import JsonValue

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredOutputSpec,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import DocxBuildEnvelope
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamItemKind,
)

DOCX_BUILD_SCHEMA_VERSION = "docx_exam_build_v12"


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


def _anchor_list(anchors: list[JsonValue], *, min_items: int | None) -> dict[str, JsonValue]:
    node: dict[str, JsonValue] = {"type": "array", "items": {"type": "string", "enum": anchors}}
    if min_items is not None:
        node["minItems"] = min_items
    return node


def docx_build_output_spec(
    *, anchors: Iterable[str], kinds: Iterable[NativeExamItemKind]
) -> StructuredOutputSpec:
    """The envelope schema with anchors and item kinds limited to one batch."""
    schema = _object(_strict_schema(DocxBuildEnvelope.model_json_schema()))
    allowed: list[JsonValue] = list(dict.fromkeys(anchors))
    definitions = _object(schema["$defs"])
    properties = _object(schema["properties"])
    properties["answer_key_anchors"] = {
        **_object(properties["answer_key_anchors"]),
        **_anchor_list(allowed, min_items=None),
    }
    for name in ("ProducedItem", "ProducedMetadata"):
        fields = _object(_object(definitions[name])["properties"])
        fields["source_anchors"] = {
            **_object(fields["source_anchors"]),
            **_anchor_list(allowed, min_items=1),
        }
    batch_kinds = frozenset(kinds)
    item_fields = _object(_object(definitions["ProducedItem"])["properties"])
    enum: list[JsonValue] = [kind.value for kind in sorted(batch_kinds, key=lambda k: k.value)]
    item_fields["kind"] = {"type": "string", "enum": enum}
    segment = _object(definitions["ProducedSegment"])
    segment_fields = _object(segment["properties"])
    description = _object(segment_fields["text"]).get("description", "")

    def segment_shape(kind: str, text: dict[str, JsonValue]) -> dict[str, JsonValue]:
        return {
            "type": "object",
            "properties": {
                "kind": {"type": "string", "enum": [kind]},
                "text": text,
                "accepted_values": segment_fields["accepted_values"],
            },
            "required": ["kind", "text", "accepted_values"],
            "additionalProperties": False,
        }

    # Text and gap segments are two shapes: a text segment requires non-empty text and
    # a gap segment requires null text, so kind and text can never disagree (O1).
    text_shape = segment_shape(
        "text", {"type": "string", "minLength": 1, "description": description}
    )
    if NativeExamItemKind.GAP_FILL in batch_kinds:
        gap_shape = segment_shape("gap", {"type": "null", "description": description})
        definitions["ProducedSegment"] = {"anyOf": [text_shape, gap_shape]}
    else:
        # Only gap_fill answers in gaps; any other kind copies a printed blank as text.
        definitions["ProducedSegment"] = text_shape
    return StructuredOutputSpec(
        schema_name="docx_exam_build",
        schema_version=DOCX_BUILD_SCHEMA_VERSION,
        json_schema=schema,
    )
