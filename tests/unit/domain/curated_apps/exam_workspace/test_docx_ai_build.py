"""Producer schema and mapping into the native exam contract."""

import json
from uuid import uuid4

import pytest
from pydantic import ValidationError

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import (
    assemble_build_result,
    native_item,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
    ProducedItem,
    ProducedSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_schema import docx_build_output_spec
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeAnswerKeyOrigin,
    NativeGap,
    NativeGapSegment,
    NativeItemReviewState,
    NativeParseOrigin,
    NativeTextSegment,
    native_export_blockers,
)

pytestmark = pytest.mark.unit


def choice_source(n=1) -> tuple[DocxChunk, ...]:
    return (
        DocxChunk(f"h{n}", "heading", f"Question {n} (1 point)"),
        DocxChunk(f"q{n}", "paragraph", "Pick a colour."),
        DocxChunk(f"c{n}", "paragraph", "A. red\nB. blue"),
        DocxChunk(f"k{n}", "paragraph", "Correct answer: B. blue"),
    )


def choice_item(n=1, **overrides) -> dict:
    return {
        "source_anchors": [f"h{n}", f"q{n}", f"c{n}"],
        "outcome": "converted",
        "review_reason": None,
        "kind": "single_choice",
        "title": f"Question {n} (1 point)",
        "body": [
            {
                "segments": [
                    {"kind": "text", "text": "Pick a colour.", "accepted_values": [], "hint": None}
                ]
            }
        ],
        "points": 1,
        "choices": [{"text": "red", "correct": False}, {"text": "blue", "correct": True}],
        **overrides,
    }


def test_strict_schema_preserves_title_properties_and_requires_every_object_field():
    schema = docx_build_output_spec().json_schema

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


def test_native_choice_assigns_ids_and_source_provenance():
    produced = ProducedItem.model_validate_json(json.dumps(choice_item()), strict=True)
    item = native_item(produced)
    assert [(choice.choice_id, choice.text) for choice in item.choices] == [
        ("choice_001", "red"),
        ("choice_002", "blue"),
    ]
    assert item.answer_key.correct_choice_ids == ("choice_002",)
    assert item.answer_key.origin is NativeAnswerKeyOrigin.SOURCE_PROVIDED
    assert item.review.state is NativeItemReviewState.REVIEW_COMPLETE
    assert item.review.parse_origin is NativeParseOrigin.LLM_PARSED
    assert item.source_anchor == "h1"
    assert item.title == "Question 1 (1 point)"
    assert item.points == 1
    assert item.plain_text_lines() == ("Pick a colour.",)


@pytest.mark.parametrize("keyed", [True, False])
def test_inline_gaps_preserve_order_keys_hints_and_block_export_without_answers(keyed):
    raw = choice_item(
        kind="gap_fill",
        choices=[],
        body=[
            {
                "segments": [
                    {"kind": "text", "text": "The sky is ", "accepted_values": [], "hint": None},
                    {
                        "kind": "gap",
                        "text": None,
                        "accepted_values": ["blue", "azure"] if keyed else [],
                        "hint": "b…",
                    },
                    {
                        "kind": "text",
                        "text": " and the grass is ",
                        "accepted_values": [],
                        "hint": None,
                    },
                    {
                        "kind": "gap",
                        "text": None,
                        "accepted_values": ["green"] if keyed else [],
                        "hint": None,
                    },
                    {"kind": "text", "text": ".", "accepted_values": [], "hint": None},
                ]
            }
        ],
    )
    produced = ProducedItem.model_validate_json(json.dumps(raw), strict=True)
    item = native_item(produced)
    assert item.body[0].segments == (
        NativeTextSegment(text="The sky is "),
        NativeGapSegment(gap_id="gap_001"),
        NativeTextSegment(text=" and the grass is "),
        NativeGapSegment(gap_id="gap_002"),
        NativeTextSegment(text="."),
    )
    assert item.gaps == (
        NativeGap(gap_id="gap_001", accepted_values=("blue", "azure") if keyed else (), hint="b…"),
        NativeGap(gap_id="gap_002", accepted_values=("green",) if keyed else ()),
    )
    assert item.answer_key.origin is (
        NativeAnswerKeyOrigin.SOURCE_PROVIDED if keyed else NativeAnswerKeyOrigin.ABSENT
    )
    result = assemble_build_result(
        document_id=uuid4(),
        filename="test.docx",
        source_sha256="a" * 64,
        chunks=choice_source(),
        accepted=((item, produced.source_anchors),),
        review_reasons={},
        key_anchors=frozenset({"k1"}),
    )
    assert [blocker.reason for blocker in native_export_blockers(result.document)] == (
        [] if keyed else ["missing_answer_key"]
    )


def test_free_text_has_not_applicable_answer_key_origin():
    produced = ProducedItem.model_validate_json(
        json.dumps(choice_item(kind="free_text", choices=[])), strict=True
    )
    assert native_item(produced).answer_key.origin is NativeAnswerKeyOrigin.NOT_APPLICABLE


def test_single_choice_with_two_correct_options_fails_the_native_contract():
    produced = ProducedItem.model_validate_json(
        json.dumps(
            choice_item(
                choices=[{"text": "red", "correct": True}, {"text": "blue", "correct": True}]
            )
        ),
        strict=True,
    )
    with pytest.raises(ValidationError, match="single_choice needs exactly one correct choice"):
        native_item(produced)


@pytest.mark.parametrize("kind,text", [("text", None), ("gap", "A misplaced answer")])
def test_produced_segment_rejects_text_in_the_wrong_kind(kind, text):
    with pytest.raises(ValidationError, match=f"{kind} segments carry"):
        ProducedSegment.model_validate_json(
            json.dumps({"kind": kind, "text": text, "accepted_values": [], "hint": None}),
            strict=True,
        )
