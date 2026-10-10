"""Producer schema sent to the provider in strict mode."""

from typing import Any

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_schema import docx_build_output_spec

pytestmark = pytest.mark.unit


def test_strict_schema_preserves_title_properties_and_requires_every_object_field():
    schema: dict[str, Any] = docx_build_output_spec().json_schema

    def visit(node):
        if isinstance(node, list):
            for entry in node:
                visit(entry)
        elif isinstance(node, dict):
            assert not {"default", "title", "discriminator", "oneOf"} & node.keys()
            if node.get("type") == "object":
                assert node["additionalProperties"] is False
                assert node["required"] == list(node["properties"])
            for key, value in node.items():
                if key in {"properties", "$defs"}:
                    for child in value.values():
                        visit(child)
                else:
                    visit(value)

    visit(schema)
    assert set(schema["properties"]) == {"title", "instructions", "answer_key_anchors", "items"}
    assert "title" in schema["$defs"]["ProducedItem"]["properties"]
