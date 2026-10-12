"""Producer schema sent to the provider in strict mode."""

import pytest
from pydantic import JsonValue

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_schema import docx_build_output_spec
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamItemKind,
)
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import (
    corpus_chunks,
    recorded_exams,
)

pytestmark = pytest.mark.unit


def _object(node: JsonValue) -> dict[str, JsonValue]:
    assert isinstance(node, dict)
    return node


def test_strict_schema_preserves_title_properties_and_requires_every_object_field():
    chunks = corpus_chunks(recorded_exams()[0])
    anchors = [chunk.anchor for chunk in chunks[:12]]
    kinds = {NativeExamItemKind.SINGLE_CHOICE, NativeExamItemKind.MULTIPLE_RESPONSE}
    schema = docx_build_output_spec(anchors=anchors, kinds=kinds).json_schema

    def visit(node: JsonValue) -> None:
        if isinstance(node, list):
            for entry in node:
                visit(entry)
        elif isinstance(node, dict):
            assert not {"default", "title", "discriminator", "oneOf"} & node.keys()
            if node.get("type") == "object":
                assert node["additionalProperties"] is False
                assert node["required"] == list(_object(node["properties"]))
            for key, value in node.items():
                if key in {"properties", "$defs"}:
                    for child in _object(value).values():
                        visit(child)
                else:
                    visit(value)

    visit(schema)
    assert set(_object(schema["properties"])) == {
        "title",
        "instructions",
        "answer_key_anchors",
        "items",
    }
    produced_item = _object(_object(schema["$defs"])["ProducedItem"])
    assert "title" in _object(produced_item["properties"])
    definitions = _object(schema["$defs"])
    item_fields = _object(_object(definitions["ProducedItem"])["properties"])
    assert _object(item_fields["kind"])["enum"] == ["multiple_response", "single_choice"]
    for node in (
        _object(_object(schema["properties"])["answer_key_anchors"]),
        _object(item_fields["source_anchors"]),
        _object(_object(_object(definitions["ProducedMetadata"])["properties"])["source_anchors"]),
    ):
        assert _object(node["items"])["enum"] == anchors
