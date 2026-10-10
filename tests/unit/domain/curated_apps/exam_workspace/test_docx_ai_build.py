"""Source-faithful native admission, strict schema and lossless fallback."""

import copy
from uuid import uuid4

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import (
    DocxBuildEntry,
    KeyEvidence,
    SourceEvidence,
    SourceText,
    assemble_build_result,
    docx_build_output_spec,
    parse_build_entry,
    validate_build_entry,
    validate_source_text,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeAnswerKey,
    NativeAnswerKeyOrigin,
    NativeChoice,
    NativeExamItem,
    NativeExamItemKind,
    NativeGap,
    NativeGapSegment,
    NativeItemReview,
    NativeItemReviewState,
    NativeParagraph,
    NativeParseOrigin,
    NativeTextSegment,
)

pytestmark = pytest.mark.unit


def choice_source(number=1):
    return (
        DocxChunk(f"q{number}", "paragraph", f"{number}. Pick a colour. (2 points)"),
        DocxChunk(f"c{number}", "paragraph", "A. red\nB. blue"),
        DocxChunk(f"k{number}", "paragraph", "Correct answer: B. blue"),
    )


def choice_entry(number=1):
    item = NativeExamItem(
        item_id="item_001",
        sequence=1,
        kind=NativeExamItemKind.SINGLE_CHOICE,
        body=(NativeParagraph(segments=(NativeTextSegment(text=f"{number}. Pick a colour."),)),),
        points=2,
        choices=(
            NativeChoice(choice_id="choice_001", text="red"),
            NativeChoice(choice_id="choice_002", text="blue"),
        ),
        answer_key=NativeAnswerKey(
            origin=NativeAnswerKeyOrigin.SOURCE_PROVIDED, correct_choice_ids=("choice_002",)
        ),
        review=NativeItemReview(
            state=NativeItemReviewState.REVIEW_REQUIRED, parse_origin=NativeParseOrigin.LLM_PARSED
        ),
    )
    return DocxBuildEntry(
        item=item,
        source_anchors=(f"q{number}", f"c{number}"),
        question_label=str(number),
        points_evidence=SourceEvidence(anchor=f"q{number}", text="2 points"),
        key_evidence=(
            KeyEvidence(
                anchor=f"k{number}",
                text="Correct answer: B. blue",
                target_id="choice_002",
                value="blue",
            ),
        ),
    )


def gap_source_and_entry():
    chunks = (
        DocxChunk("heading", "heading", "Section X: completion (1 poäng)"),
        DocxChunk("q", "paragraph", "The sky is ___ today."),
        DocxChunk("k", "paragraph", "Correct answer: blue"),
    )
    item = NativeExamItem(
        item_id="item_001",
        sequence=1,
        kind=NativeExamItemKind.GAP_FILL,
        title=chunks[0].text,
        body=(
            NativeParagraph(
                segments=(
                    NativeTextSegment(text="The sky is "),
                    NativeGapSegment(gap_id="gap_001"),
                    NativeTextSegment(text=" today."),
                )
            ),
        ),
        points=1,
        gaps=(NativeGap(gap_id="gap_001", accepted_values=("blue",)),),
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.SOURCE_PROVIDED),
        review=NativeItemReview(
            state=NativeItemReviewState.REVIEW_REQUIRED, parse_origin=NativeParseOrigin.LLM_PARSED
        ),
    )
    entry = DocxBuildEntry(
        item=item,
        source_anchors=("heading", "q"),
        question_label=chunks[0].text,
        points_evidence=SourceEvidence(anchor="heading", text="1 poäng"),
        key_evidence=(
            KeyEvidence(anchor="k", text=chunks[2].text, target_id="gap_001", value="blue"),
        ),
    )
    return chunks, entry


def test_accepts_inline_choice_and_heading_gap_with_source_provenance():
    choice = validate_build_entry(choice_entry(), choice_source())
    chunks, entry = gap_source_and_entry()
    gap = validate_build_entry(entry, chunks)
    for item in (choice, gap):
        assert item.review.state is NativeItemReviewState.REVIEW_COMPLETE
        assert item.review.parse_origin is NativeParseOrigin.LLM_PARSED
        assert item.answer_key.origin is NativeAnswerKeyOrigin.SOURCE_PROVIDED


@pytest.mark.parametrize("field,value", [("title", "Invented title"), ("points", 3)])
def test_rejects_invented_title_and_changed_points(field, value):
    raw = choice_entry().model_dump(mode="json")
    raw["item"][field] = value
    with pytest.raises(ValueError):
        validate_build_entry(parse_build_entry(raw), choice_source())


@pytest.mark.parametrize("annotation", ["12 points", "1.2 points", "1,2 points"])
def test_rejects_suffix_quote_as_source_points(annotation):
    source = choice_source()
    chunks = (
        DocxChunk("q1", "paragraph", source[0].text.replace("2 points", annotation)),
        *source[1:],
    )
    # Reviewer probe: retain points=2 and quote='2 points' despite a larger
    # complete annotation in the source.
    with pytest.raises(ValueError, match="Poängen stämmer"):
        validate_build_entry(choice_entry(), chunks)


@pytest.mark.parametrize(
    "annotation,points", [("12 points", 12), ("1.2 points", 1.2), ("1,2 poäng", 1.2)]
)
def test_accepts_complete_source_points_annotation(annotation, points):
    source = choice_source()
    chunks = (
        DocxChunk("q1", "paragraph", source[0].text.replace("2 points", annotation)),
        *source[1:],
    )
    entry = choice_entry().model_copy(
        update={
            "item": choice_entry().item.model_copy(update={"points": points}),
            "points_evidence": SourceEvidence(anchor="q1", text=annotation),
        }
    )
    assert validate_build_entry(entry, chunks).points == points


def test_option_label_cannot_bind_another_questions_numbered_key():
    chunks = (
        DocxChunk("q2", "paragraph", "2. Pick a colour. (2 points)"),
        DocxChunk("c2", "paragraph", "1. red\n2. blue"),
        DocxChunk("facit", "heading", "Answer key"),
        DocxChunk("keys", "paragraph", "1. red\n2. blue"),
    )
    raw = choice_entry(2).model_dump(mode="json")
    raw["question_label"] = "1"
    raw["item"]["answer_key"]["correct_choice_ids"] = ["choice_001"]
    raw["key_evidence"][0].update(anchor="keys", text="1. red", target_id="choice_001", value="red")
    with pytest.raises(ValueError, match="Frågans nummer"):
        validate_build_entry(parse_build_entry(raw), chunks)
    raw["question_label"] = "2"
    raw["item"]["answer_key"]["correct_choice_ids"] = ["choice_002"]
    raw["key_evidence"][0].update(text="2. blue", target_id="choice_002", value="blue")
    admitted = validate_build_entry(parse_build_entry(raw), chunks)
    assert admitted.answer_key.correct_choice_ids == ("choice_002",)
    assert admitted.answer_key.origin is NativeAnswerKeyOrigin.SOURCE_PROVIDED


@pytest.mark.parametrize("target", ["body", "choice"])
def test_rejects_invented_student_text(target):
    raw = choice_entry().model_dump(mode="json")
    if target == "body":
        raw["item"]["body"][0]["segments"][0]["text"] = "Solve another question."
    else:
        raw["item"]["choices"][0]["text"] = "purple"
    with pytest.raises(ValueError, match="Texten"):
        validate_build_entry(parse_build_entry(raw), choice_source())


def test_rejects_choice_presence_as_proof_and_wrong_inline_key():
    raw = choice_entry().model_dump(mode="json")
    raw["item"]["answer_key"]["correct_choice_ids"] = ["choice_001"]
    raw["key_evidence"][0].update(target_id="choice_001", value="red")
    with pytest.raises(ValueError, match="Facitvärdet"):
        validate_build_entry(parse_build_entry(raw), choice_source())
    raw["key_evidence"][0].update(anchor="c1", text="A. red")
    with pytest.raises(ValueError):
        validate_build_entry(parse_build_entry(raw), choice_source())


def test_rejects_cross_question_inline_key():
    raw = choice_entry().model_dump(mode="json")
    raw["key_evidence"][0]["anchor"] = "k2"
    with pytest.raises(ValueError, match="angränsande"):
        validate_build_entry(parse_build_entry(raw), (*choice_source(), *choice_source(2)))


@pytest.mark.parametrize("mutation", ["invented_answer", "wrong_answer", "hint", "placement"])
def test_rejects_gap_key_hint_and_placement(mutation):
    chunks, entry = gap_source_and_entry()
    raw = entry.model_dump(mode="json")
    if mutation in {"invented_answer", "wrong_answer"}:
        raw["item"]["gaps"][0]["accepted_values"] = ["orange"]
        raw["key_evidence"][0]["value"] = "orange"
        if mutation == "invented_answer":
            raw["key_evidence"][0]["text"] = "Correct answer: orange"
    elif mutation == "hint":
        raw["item"]["gaps"][0]["hint"] = "Starts with b"
    else:
        raw["item"]["body"][0]["segments"].reverse()
    with pytest.raises(ValueError):
        validate_build_entry(parse_build_entry(raw), chunks)


def test_numbered_section_key_requires_question_number():
    chunks = (
        *choice_source()[:2],
        DocxChunk("facit", "heading", "Answer key"),
        DocxChunk("key", "paragraph", "1. B\n2. A"),
    )
    raw = choice_entry().model_dump(mode="json")
    raw["key_evidence"][0].update(anchor="key", text="1. B")
    assert validate_build_entry(parse_build_entry(raw), chunks).points == 2
    raw["key_evidence"][0]["text"] = "2. A"
    with pytest.raises(ValueError):
        validate_build_entry(parse_build_entry(raw), chunks)


@pytest.mark.parametrize(
    "mutation", ["missing_native_field", "extra_field", "wrong_kind", "invalid_points"]
)
def test_schema_mismatch_rejected_independently(mutation):
    raw = choice_entry().model_dump(mode="json")
    if mutation == "missing_native_field":
        del raw["item"]["gaps"]
    elif mutation == "extra_field":
        raw["item"]["surprise"] = "ignored"
    elif mutation == "wrong_kind":
        raw["item"]["kind"] = "free_text"
    else:
        raw["item"]["points"] = "2"
    with pytest.raises(ValueError):
        parse_build_entry(raw)


def test_strict_schema_has_all_required_fields_and_supported_unions():
    schema = docx_build_output_spec().json_schema

    def visit(node):
        if isinstance(node, dict):
            assert not {"default", "discriminator", "oneOf"} & set(node)
            if node.get("type") == "object":
                assert node["additionalProperties"] is False
                assert set(node["required"]) == set(node["properties"])
            for child in node.values():
                visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)

    visit(schema)
    raw = choice_entry().model_dump(mode="json")
    assert parse_build_entry(copy.deepcopy(raw)).item.kind is NativeExamItemKind.SINGLE_CHOICE


def test_metadata_and_teacher_key_notes_accounted_other_chunks_preserved():
    source = (
        DocxChunk("title", "heading", "A test"),
        *choice_source(),
        DocxChunk("lost", "table", "Unparsed source\nwith a table"),
    )
    entry = choice_entry()
    item = validate_build_entry(entry, source)
    result = assemble_build_result(
        document_id=uuid4(),
        filename="test.docx",
        source_sha256="a" * 64,
        chunks=source,
        accepted=((item, entry.source_anchors),),
        title=SourceText(text="A test", source_anchors=("title",)),
        reason="Kräver granskning.",
    )
    assert result.document.title == "A test"
    assert [i.item_id for i in result.document.items] == ["item_001", "item_002"]
    assert result.document.items[1].plain_text_lines() == ("Unparsed source\nwith a table",)
    assert "Correct answer: B. blue" in result.notes
    assert result.document.items[1].review.reasons == ("Kräver granskning.",)


def test_fallback_keeps_every_chunk_even_answer_key_and_title():
    source = (DocxChunk("title", "heading", "A test"), *choice_source())
    result = assemble_build_result(
        document_id=uuid4(),
        filename="test.docx",
        source_sha256="a" * 64,
        chunks=source,
        reason="AI avstängd.",
    )
    assert [i.source_anchor for i in result.document.items] == [c.anchor for c in source]
    assert all(
        i.review.state is NativeItemReviewState.REVIEW_REQUIRED for i in result.document.items
    )
    assert result.input_tokens is result.output_tokens is None
    with pytest.raises(ValueError):
        validate_source_text(SourceText(text="Invented", source_anchors=("title",)), source)


def test_multiple_response_preserves_complete_source_key_and_rejects_missing_correct_choice():
    chunks = (*choice_source()[:2], DocxChunk("k1", "paragraph", "Correct answers: A; B"))
    raw = choice_entry().model_dump(mode="json")
    raw["item"]["kind"] = "multiple_response"
    raw["item"]["answer_key"]["correct_choice_ids"] = ["choice_001", "choice_002"]
    raw["key_evidence"] = [
        {
            "anchor": "k1",
            "text": "Correct answers: A; B",
            "target_id": "choice_001",
            "value": "red",
        },
        {
            "anchor": "k1",
            "text": "Correct answers: A; B",
            "target_id": "choice_002",
            "value": "blue",
        },
    ]
    assert (
        validate_build_entry(parse_build_entry(raw), chunks).kind
        is NativeExamItemKind.MULTIPLE_RESPONSE
    )
    raw["item"]["answer_key"]["correct_choice_ids"] = ["choice_002"]
    raw["key_evidence"] = raw["key_evidence"][1:]
    with pytest.raises(ValueError, match="hela facitraden"):
        validate_build_entry(parse_build_entry(raw), chunks)


def test_claimed_chunk_cannot_hide_dropped_source_text_or_choice():
    chunks = (
        choice_source()[0],
        DocxChunk("c1", "paragraph", "A. red\nB. blue\nC. green"),
        choice_source()[2],
    )
    with pytest.raises(ValueError, match="obehandlade"):
        validate_build_entry(choice_entry(), chunks)


def test_free_text_has_not_applicable_key_and_llm_origin():
    chunks = (DocxChunk("q1", "paragraph", "1. Explain your answer. (3 p)"),)
    item = NativeExamItem(
        item_id="item_001",
        sequence=1,
        kind=NativeExamItemKind.FREE_TEXT,
        body=(NativeParagraph(segments=(NativeTextSegment(text=chunks[0].text),)),),
        points=3,
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
        review=NativeItemReview(
            state=NativeItemReviewState.REVIEW_REQUIRED, parse_origin=NativeParseOrigin.LLM_PARSED
        ),
    )
    entry = DocxBuildEntry(
        item=item,
        source_anchors=("q1",),
        question_label="1",
        points_evidence=SourceEvidence(anchor="q1", text="3 p"),
        key_evidence=(),
    )
    accepted = validate_build_entry(entry, chunks)
    assert accepted.answer_key.origin is NativeAnswerKeyOrigin.NOT_APPLICABLE
    assert accepted.review.state is NativeItemReviewState.REVIEW_COMPLETE
