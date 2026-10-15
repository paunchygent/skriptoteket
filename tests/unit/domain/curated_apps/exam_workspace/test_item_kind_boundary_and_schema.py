"""One gap_fill/free_text definition and a reply schema without empty text (39-05-08).

D1/D2: the labeler's descriptions and instruction and the converter's kind rule all carry
the same written boundary, including the alternative-sentences rule. O1: the strict reply
schema forbids empty text segments, and null text in a batch without gaps.
"""

import pytest
from jsonschema import Draft202012Validator  # type: ignore[import-untyped]
from pydantic import ValidationError

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_prompt import (
    docx_build_prompt,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import ProducedSegment
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_schema import docx_build_output_spec
from skriptoteket.domain.curated_apps.exam_workspace.item_kind_boundary import (
    FREE_TEXT_DEFINITION,
    GAP_FILL_DEFINITION,
    converter_kind_rule,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
)
from skriptoteket.infrastructure.llm.openai.decisions_item_labeler import (
    CLASSIFICATION_INSTRUCTION,
    LABEL_DESCRIPTIONS,
)
from skriptoteket.protocols.item_type_labeler import ItemTypeLabel

_ALTERNATIVE_SENTENCES = "alternative sentences for one answer line"


def test_the_boundary_definition_states_the_alternative_sentences_rule() -> None:
    assert _ALTERNATIVE_SENTENCES in GAP_FILL_DEFINITION
    assert "gap_fill" in FREE_TEXT_DEFINITION  # length alone never makes free_text


def test_labeler_texts_are_generated_from_the_one_definition() -> None:
    assert LABEL_DESCRIPTIONS[ItemTypeLabel.GAP_FILL].startswith(GAP_FILL_DEFINITION)
    assert LABEL_DESCRIPTIONS[ItemTypeLabel.FREE_TEXT].startswith(FREE_TEXT_DEFINITION)
    assert GAP_FILL_DEFINITION in CLASSIFICATION_INSTRUCTION
    assert FREE_TEXT_DEFINITION in CLASSIFICATION_INSTRUCTION


@pytest.mark.parametrize("kind", list(NativeExamItemKind))
def test_every_converter_prompt_carries_the_same_definition(kind: NativeExamItemKind) -> None:
    prompt = docx_build_prompt(frozenset({kind}))
    assert converter_kind_rule() in prompt
    assert _ALTERNATIVE_SENTENCES in prompt
    assert "item title" not in prompt


def test_a_batch_prompt_carries_only_the_sections_of_its_kinds() -> None:
    gap_fill = docx_build_prompt(frozenset({NativeExamItemKind.GAP_FILL}))
    choice = docx_build_prompt(frozenset({NativeExamItemKind.SINGLE_CHOICE}))
    both = docx_build_prompt(
        frozenset({NativeExamItemKind.GAP_FILL, NativeExamItemKind.MULTIPLE_RESPONSE})
    )

    assert "Where each gap goes" in gap_fill and "Where each gap goes" not in choice
    assert "correct marks each option" in choice and "correct marks each option" not in gap_fill
    assert "Where each gap goes" in both and "correct marks each option" in both
    assert "match_left holds" not in both
    # The core names every kind so a batch can report a kind it was not given.
    assert "outcome type_conflict" in gap_fill and "matching:" in gap_fill


def _object(value: object) -> dict[str, object]:
    assert isinstance(value, dict)
    return value


def _segment_schema(kind: NativeExamItemKind) -> dict[str, object]:
    spec = docx_build_output_spec(anchors=["body:0001"], kinds=[kind])
    definitions = _object(spec.json_schema["$defs"])
    return _object(definitions["ProducedSegment"])


def _segment_errors(kind: NativeExamItemKind, segment: dict[str, object]) -> list[str]:
    validator = Draft202012Validator(_segment_schema(kind))
    return [error.message for error in validator.iter_errors(segment)]


def test_schema_forbids_empty_text_and_null_text_without_gaps() -> None:
    properties = _object(_segment_schema(NativeExamItemKind.FREE_TEXT)["properties"])
    text = _object(properties["text"])
    assert text["type"] == "string"
    assert text["minLength"] == 1
    assert _object(properties["kind"])["enum"] == ["text"]


def test_gap_batch_schema_admits_only_the_text_and_gap_segment_shapes() -> None:
    admitted: list[dict[str, object]] = [
        {
            "kind": "text",
            "text": "Cellen har",
            "accepted_values": [],
            "asset_id": None,
        },
        {
            "kind": "gap",
            "text": None,
            "accepted_values": ["en kärna"],
            "asset_id": None,
        },
    ]
    rejected: list[dict[str, object]] = [
        {
            "kind": "text",
            "text": None,
            "accepted_values": [],
            "asset_id": None,
        },
        {
            "kind": "text",
            "text": "",
            "accepted_values": [],
            "asset_id": None,
        },
        {
            "kind": "gap",
            "text": "en kärna",
            "accepted_values": [],
            "asset_id": None,
        },
    ]
    for segment in admitted:
        assert _segment_errors(NativeExamItemKind.GAP_FILL, segment) == []
    for segment in rejected:
        assert _segment_errors(NativeExamItemKind.GAP_FILL, segment) != []


def test_schema_has_no_item_title() -> None:
    spec = docx_build_output_spec(anchors=["body:0001"], kinds=[NativeExamItemKind.FREE_TEXT])
    definitions = _object(spec.json_schema["$defs"])
    properties = _object(_object(definitions["ProducedItem"])["properties"])
    assert "title" not in properties


@pytest.mark.parametrize("text", ["", None])
def test_produced_text_segment_rejects_empty_or_null_text(text: str | None) -> None:
    with pytest.raises(ValidationError):
        ProducedSegment.model_validate({"kind": "text", "text": text, "accepted_values": []})
