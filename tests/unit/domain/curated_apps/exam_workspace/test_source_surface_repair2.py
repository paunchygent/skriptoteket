"""Adversarial source ownership and mixed-surface heading recovery regressions."""

from dataclasses import replace

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import aligned_native_item
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import ProducedItem
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import (
    DocxChunk,
    DocxImage,
    DocxSourceParagraph,
    DocxSourceRun,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeAssetSegment,
    NativeGapSegment,
    NativeSegment,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_plain_text
from skriptoteket.domain.curated_apps.exam_workspace.source_format_coverage import (
    complete_source_formatting,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_formatting import (
    SourceFormatting,
    formatted_text,
)

pytestmark = pytest.mark.unit


def _as_text(segment: NativeSegment) -> NativeTextSegment:
    assert isinstance(segment, NativeTextSegment)
    return segment


def _chunk(anchor, text, *, heading=None, marks=()):
    return DocxChunk(
        anchor,
        "paragraph",
        text,
        text,
        runs=(DocxSourceRun(0, text, marks),),
        paragraphs=(DocxSourceParagraph(0, text, heading),),
    )


def _item(chunks, texts, **overrides):
    return ProducedItem.model_validate(
        {
            "source_anchors": [chunk.anchor for chunk in chunks],
            "outcome": "converted",
            "review_reason": None,
            "kind": "free_text",
            "printed_label": "1",
            "points": None,
            "key_source": None,
            "facit_text": None,
            "choices": [],
            "body": [
                {"segments": [{"kind": "text", "text": text, "accepted_values": []}]}
                for text in texts
            ],
            **overrides,
        }
    )


@pytest.mark.parametrize(
    "continuation",
    [
        "100 degrees is the boiling temperature.",
        "1.5 metres is the measured distance.",
        "1. Repeat this numbered content.",
    ],
)
def test_question_label_omission_never_deletes_continuation_content(continuation):
    chunks = (
        _chunk("body:0001", "1. Read the values."),
        _chunk("body:0002", continuation, marks=("bold",)),
    )
    paths: list[str] = []
    result = aligned_native_item(
        _item(chunks, ["Read the values.", "State the measured value."]),
        chunks=chunks,
        language="en",
        formatting_observer=paths.append,
    ).item
    assert body_plain_text(result.body) == "Read the values.\n" + continuation
    assert _as_text(result.body[1].segments[0]).marks == ("bold",)
    assert paths == ["rebuilt"]


@pytest.mark.parametrize("label", ["Question 1", "Fråga 1", "a"])
def test_question_label_span_handles_named_and_letter_labels(label):
    chunks = (
        _chunk("body:0001", label + ". Identify the important concept.", marks=("bold",)),
        _chunk("body:0002", label + ". Repeat this content.", marks=("italic",)),
    )
    source = SourceFormatting(chunks, ignored=(label,))
    result = source.rebuild_body({})
    assert (
        body_plain_text(result)
        == "Identify the important concept.\n" + label + ". Repeat this content."
    )


def test_question_label_span_does_not_consume_body_punctuation_after_its_separator():
    chunks = (_chunk("body:0001", "1. .NET is the important concept.", marks=("bold",)),)
    source = SourceFormatting(chunks, ignored=("1",))
    result = formatted_text("NET is the important concept.", source)
    result = complete_source_formatting(
        chunks, (source,), source, result, printed_label="1", answers={}, can_rebuild_body=True
    )
    assert body_plain_text(result) == ".NET is the important concept."


def test_question_label_coverage_does_not_exempt_a_numeric_prefix():
    chunks = (_chunk("body:0001", "100 degrees", marks=("bold",)),)
    source = SourceFormatting(chunks, ignored=("1",))
    body = formatted_text("00 degrees", source)
    result = complete_source_formatting(
        chunks, (source,), source, body, printed_label="1", answers={}, can_rebuild_body=True
    )
    assert body_plain_text(result) == "100 degrees"
    assert source.path == "rebuilt"


@pytest.mark.parametrize("heading_at_end", [False, True])
@pytest.mark.parametrize("wording", ["Choose an answer.", "Select whichever hue you prefer."])
def test_omitted_size_heading_merges_into_body_without_copying_choices(heading_at_end, wording):
    heading = _chunk("body:0002", "Read this section carefully.", heading=2)
    prompt = _chunk("body:0001", "1. Choose an answer.")
    options = (_chunk("body:0003", "A. red"), _chunk("body:0004", "B. blue"))
    chunks = (prompt, heading, *options) if heading_at_end else (heading, prompt, *options)
    paths: list[str] = []
    result = aligned_native_item(
        _item(
            chunks,
            [wording],
            kind="single_choice",
            choices=[{"text": "red", "correct": False}, {"text": "blue", "correct": False}],
        ),
        chunks=chunks,
        language="en",
        formatting_observer=paths.append,
    ).item
    expected = [wording, "Read this section carefully."]
    if not heading_at_end:
        expected.reverse()
    assert body_plain_text(result.body) == "\n".join(expected)
    assert [p.heading_level for p in result.body] == ([None, 2] if heading_at_end else [2, None])
    assert [body_plain_text(c.body) for c in result.choices] == ["red", "blue"]
    assert paths == ["rebuilt"]


def test_heading_recovery_retains_picture_and_gap_atoms_in_their_native_paragraph():
    image = DocxImage(payload=b"picture", media_type="image/png", offset=0, marked_offset=0)
    prompt = replace(_chunk("body:0002", "1. The answer is ___."), images=(image,))
    heading = _chunk("body:0001", "Complete this section.", heading=3)
    chunks = (heading, prompt)
    produced = _item(
        chunks,
        [],
        kind="gap_fill",
        key_source="copied",
        facit_text="red",
        body=[
            {
                "segments": [
                    {
                        "kind": "asset",
                        "text": None,
                        "accepted_values": [],
                        "asset_id": image.asset_id,
                    },
                    {"kind": "text", "text": "The answer is ", "accepted_values": []},
                    {"kind": "gap", "text": None, "accepted_values": ["red"]},
                    {"kind": "text", "text": ".", "accepted_values": []},
                ]
            }
        ],
    )
    result = aligned_native_item(produced, chunks=chunks, language="en").item
    assert result.body[0].heading_level == 3
    assert body_plain_text(result.body).startswith("Complete this section.\n")
    assert [s.kind for s in result.body[1].segments] == ["asset", "text", "gap", "text"]
    asset = result.body[1].segments[0]
    assert isinstance(asset, NativeAssetSegment)
    assert asset.asset_id == image.asset_id
    gap = result.body[1].segments[2]
    assert isinstance(gap, NativeGapSegment)
    assert gap.gap_id == result.gaps[0].gap_id


@pytest.mark.parametrize("repeat_after_heading", [False, True])
def test_heading_merge_orders_standalone_pictures_around_the_recovered_heading(
    repeat_after_heading,
):
    image = DocxImage(payload=b"picture", media_type="image/png", offset=0, marked_offset=0)
    drawing = replace(_chunk("body:0001", ""), images=(image,))
    heading = _chunk("body:0002", "Read this section carefully.", heading=2)
    prompt = _chunk("body:0003", "1. Explain the picture.")
    repeated = replace(drawing, anchor="body:0004")
    chunks = (
        (drawing, heading, repeated, prompt) if repeat_after_heading else (drawing, heading, prompt)
    )
    produced = _item(chunks, ["Explain the picture."])
    picture: dict[str, list[dict[str, object]]] = {
        "segments": [
            {"kind": "asset", "text": None, "accepted_values": [], "asset_id": image.asset_id}
        ]
    }
    produced = produced.model_validate(
        {
            **produced.model_dump(),
            "body": [
                *([picture] * (2 if repeat_after_heading else 1)),
                *produced.model_dump()["body"],
            ],
        }
    )
    result = aligned_native_item(produced, chunks=chunks, language="en").item
    assert result.body[0].segments[0].kind == "asset"
    assert result.body[1].heading_level == 2
    if repeat_after_heading:
        assert result.body[2].segments[0].kind == "asset"
        assert (
            body_plain_text((result.body[1], result.body[3]))
            == "Read this section carefully.\nExplain the picture."
        )
    else:
        assert (
            body_plain_text(result.body[1:]) == "Read this section carefully.\nExplain the picture."
        )
