"""DOCX build output: the producer schema and the native body projection (W10)."""

from uuid import uuid4

import pytest
from pydantic import JsonValue

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import (
    aligned_native_item,
    assemble_build_result,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
    ProducedItem,
    ProducedParagraph,
    ProducedSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_schema import docx_build_output_spec
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import (
    DocxChunk,
    DocxSourceParagraph,
    DocxSourceRun,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeGapSegment,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
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
    assert "title" not in _object(produced_item["properties"])
    definitions = _object(schema["$defs"])
    item_fields = _object(_object(definitions["ProducedItem"])["properties"])
    assert _object(item_fields["kind"])["enum"] == ["multiple_response", "single_choice"]
    for node in (
        _object(_object(schema["properties"])["answer_key_anchors"]),
        _object(item_fields["source_anchors"]),
        _object(_object(_object(definitions["ProducedMetadata"])["properties"])["source_anchors"]),
    ):
        assert _object(node["items"])["enum"] == anchors


def _text_paragraph(text: str) -> ProducedParagraph:
    return ProducedParagraph(
        segments=(ProducedSegment(kind="text", text=text, accepted_values=()),)
    )


def _gap_paragraph(*accepted: str) -> ProducedParagraph:
    return ProducedParagraph(
        segments=(ProducedSegment(kind="gap", text=None, accepted_values=accepted),)
    )


def _item(
    *paragraphs: ProducedParagraph,
    kind: NativeExamItemKind = NativeExamItemKind.FREE_TEXT,
) -> ProducedItem:
    keyed = kind is not NativeExamItemKind.FREE_TEXT
    return ProducedItem(
        source_anchors=("body:0001",),
        outcome="converted",
        review_reason=None,
        kind=kind,
        printed_label=None,
        key_source="copied" if keyed else None,
        facit_text="svar" if keyed else None,
        body=tuple(paragraphs),
        points=1,
        choices=(),
        match_left=(),
        match_right=(),
        match_pairs=(),
        criteria=(),
    )


def _body_text(item: NativeExamItem) -> list[str]:
    return [
        "".join(
            segment.text for segment in paragraph.segments if isinstance(segment, NativeTextSegment)
        )
        for paragraph in item.body
    ]


def test_underscore_answer_lines_never_reach_a_free_text_body() -> None:
    item = aligned_native_item(
        _item(_text_paragraph("Förklara."), _text_paragraph("_____"), _text_paragraph("  __ _  ")),
        language="sv",
    ).item

    assert _body_text(item) == ["Förklara."]


def test_a_source_backed_marked_answer_line_never_reaches_a_free_text_body() -> None:
    chunks = (
        DocxChunk("body:0001", "paragraph", "Förklara.", "Förklara."),
        DocxChunk(
            "body:0002",
            "paragraph",
            "_____",
            "_____",
            runs=(DocxSourceRun(0, "_____", ("underline",)),),
            paragraphs=(DocxSourceParagraph(0, "_____"),),
        ),
    )
    item = aligned_native_item(
        _item(_text_paragraph("Förklara."), _text_paragraph("_____")),
        chunks=chunks,
        language="sv",
    ).item

    assert _body_text(item) == ["Förklara."]


def test_a_free_text_paragraph_of_only_a_model_gap_is_dropped() -> None:
    item = aligned_native_item(
        _item(_text_paragraph("Förklara."), _gap_paragraph()),
        language="sv",
    ).item

    assert _body_text(item) == ["Förklara."]


def test_a_free_text_label_keeps_its_gap_blank() -> None:
    item = aligned_native_item(
        _item(
            ProducedParagraph(
                segments=(
                    ProducedSegment(kind="text", text="Svar: ", accepted_values=()),
                    ProducedSegment(kind="gap", text=None, accepted_values=()),
                )
            )
        ),
        language="sv",
    ).item

    assert _body_text(item) == ["Svar: ____"]


def test_dash_and_dot_lines_are_kept() -> None:
    item = aligned_native_item(
        _item(_text_paragraph("-------"), _text_paragraph(".......")),
        language="sv",
    ).item

    assert _body_text(item) == ["-------", "......."]


def test_a_gap_fill_paragraph_with_only_a_gap_is_kept() -> None:
    item = aligned_native_item(
        _item(_gap_paragraph("svar"), kind=NativeExamItemKind.GAP_FILL),
        language="sv",
    ).item

    (paragraph,) = item.body
    assert paragraph.segments == (NativeGapSegment(gap_id="gap_001"),)


def _source_chunk(anchor: str, text: str) -> DocxChunk:
    return DocxChunk(anchor, "paragraph", text, text)


def _review_result(chunks: tuple[DocxChunk, ...]):
    return assemble_build_result(
        document_id=uuid4(),
        filename="prov.docx",
        source_sha256="0" * 64,
        chunks=chunks,
        review_reasons={chunk.anchor: "Granska manuellt." for chunk in chunks},
    )


def test_an_answer_line_chunk_between_questions_yields_no_review_item() -> None:
    chunks = (
        _source_chunk("body:0001", "Fråga ett?"),
        _source_chunk("body:0002", "  _____  "),
        _source_chunk("body:0003", "Fråga två?"),
    )

    result = _review_result(chunks)

    bodies = [item.plain_text_lines() for item in result.document.items]
    assert bodies == [("Fråga ett?",), ("Fråga två?",)]
    assert all("Tomt källstycke." not in line for body in bodies for line in body)
    assert all(line.strip("_ ") != "" for body in bodies for line in body)


def test_a_labelled_answer_line_chunk_still_yields_a_review_item() -> None:
    chunks = (_source_chunk("body:0001", "Svar: ____"),)

    result = _review_result(chunks)

    assert [line for item in result.document.items for line in item.plain_text_lines()] == [
        "Svar: ____"
    ]
