"""A source part markdown cannot carry reaches the labeler as an image of that part (D14, R-F5).

The production pipeline converts exams built in Word: a table with a merged cell, a picture
or a text box in a paragraph of its own, and a picture in a format no image can be made of.
The Decisions first pass is the real HTTP adapter; only the network is replaced.
"""

import json

import pytest
from pydantic import JsonValue

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import asset_id_for
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_export_rules import (
    native_export_blockers,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_labeler_markdown import (  # noqa: E501
    PythonDocxLabelerMarkdown,
)
from skriptoteket.protocols.docx_conversion_progress import ConversionPhase
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import (
    RecordingProgress,
)
from tests.unit.application.curated_apps.handlers.docx_source_image_support import (
    BETWEEN_GROUPING,
    DRAWN_GROUPING,
    GROUPING,
    PICTURE_STEM,
    TABLE_STEM,
    between_exam,
    convert,
    converted,
    drawn_exam,
    part_image,
    picture_png,
    table_exam,
)

pytestmark = pytest.mark.unit


@pytest.mark.asyncio
async def test_a_merged_cell_reaches_the_labeler_as_an_image_and_a_lost_picture_is_explicit():
    decisions, provider, outcome = await convert(table_exam(), GROUPING)

    (labeling,) = decisions
    assert [q.name for q in labeling.questions] == ["kind_q1"], "q2 must not be labeled"
    assert not isinstance(labeling.input, str), "the source images must go in"
    (message,) = labeling.input
    parts = message.content
    assert [part.type for part in parts] == ["input_text", "input_image"]
    assert parts[0].text.endswith(f"### Question q1\n1. {TABLE_STEM}")
    assert "springa" not in parts[0].text, "the table must not also go in as text"
    image = part_image(parts[1])
    assert image.width > 0 and image.height > 0

    events = [e for e in outcome.result.events if e.code == "labeler_source_image_unavailable"]
    assert [e.anchors for e in events] == [("body:0004",)]
    converted = [r.item_id for r in provider.requests if r.item_id.startswith("docx_")]
    assert "docx_wi-01" not in converted, "a named missing picture must not reach conversion"
    assert any(
        "figur.emf" in reason
        for item in outcome.result.document.items
        for reason in item.review.reasons
    )
    assert any(event.code == "source_picture_missing" for event in outcome.result.events)
    assert outcome.update.pending == ()


def test_a_block_with_only_a_drawing_is_projected_at_its_source_position():
    source = PythonDocxLabelerMarkdown().source(content=drawn_exam())

    assert [chunk.anchor for chunk in source.chunks] == [f"body:{i:04d}" for i in range(1, 9)]
    assert sorted(source.images) == ["body:0003", "body:0006"]
    assert list(source.unavailable) == ["body:0008"]


@pytest.mark.asyncio
async def test_a_picture_or_text_box_alone_in_its_paragraph_reaches_the_labeler_and_converter():
    decisions, provider, outcome = await convert(drawn_exam(), DRAWN_GROUPING)

    (grouping,) = [r for r in provider.requests if r.item_id.startswith("docx_grouping")]
    for anchor in ("body:0003", "body:0006", "body:0008"):
        assert f"[{anchor}]" in grouping.user_payload, "grouping must see every drawn block"

    (labeling,) = decisions
    assert [q.name for q in labeling.questions] == ["kind_q1", "kind_q2"]
    assert not isinstance(labeling.input, str), "the source images must go in"
    (message,) = labeling.input
    parts = message.content
    assert [part.type for part in parts] == ["input_text", "input_image"] * 2
    assert parts[0].text.endswith(f"### Question q1\n1. {PICTURE_STEM}")
    assert parts[2].text.startswith("\nSvara med en mening."), "the picture stands before it"
    assert parts[2].text.endswith("### Question q2\n2. Vad står i rutan?")
    assert all("Ja eller nej" not in part.text for part in parts), "a text box is drawn, not typed"
    assert part_image(parts[1]).width > 0 and part_image(parts[3]).width > 0

    events = [e for e in outcome.result.events if e.code == "labeler_source_image_unavailable"]
    assert [e.anchors for e in events] == [("body:0008",)]
    batches = {
        r.item_id: r.user_payload for r in provider.requests if r.item_id.startswith("docx_w")
    }
    assert not any(item_id.startswith("docx_wi") for item_id in batches), (
        "the missing EMF is review-only"
    )
    missing_question = next(
        item
        for item in outcome.result.document.items
        if any("figur.emf" in reason for reason in item.review.reasons)
    )
    assert missing_question.review.state.value == "review_required"
    assert missing_question.retry_source is not None
    assert missing_question.retry_source.has_missing_pictures()
    assert any(
        blocker.item_id == missing_question.item_id and blocker.reason == "unbuilt_question"
        for blocker in native_export_blockers(outcome.result.document)
    )
    labeled = "".join(
        payload for item_id, payload in batches.items() if item_id.startswith("docx_w1")
    )
    assert '"body:0003"' in labeled and '"body:0006"' in labeled
    assert outcome.update.pending == ()


@pytest.mark.asyncio
@pytest.mark.parametrize("carried", [True, False], ids=["carrier-placed", "carrier-missing"])
async def test_a_picture_between_two_questions_places_the_carrier_or_falls_back_to_source(
    carried: bool,
):
    asset_id = asset_id_for(picture_png())
    first = converted(
        f"1. {PICTURE_STEM}",
        *((2, 3) if carried else (2,)),
        asset_ids=(asset_id,) if carried else (),
    )
    items = (first, converted("2. Beskriv vädret i dag.", 4))

    title: dict[str, JsonValue] = {"text": "Bildfrågor", "source_anchors": ["body:0001"]}

    _, provider, outcome = await convert(between_exam(), BETWEEN_GROUPING, items, title)

    (grouping,) = [r for r in provider.requests if r.item_id.startswith("docx_grouping")]
    assert f'[body:0003] (drawing) <image asset_id="{asset_id}"/>' in grouping.user_payload
    (holding,) = [
        r
        for r in provider.requests
        if r.item_id.startswith("docx_w") and '"body:0003"' in r.user_payload
    ]
    payload = json.loads(holding.user_payload)
    assert {
        "anchor": "body:0003",
        "kind": "drawing",
        "text": f'<image asset_id="{asset_id}"/>',
    } in payload["chunks"]

    document = outcome.result.document
    assert document.title == "Bildfrågor"
    placed = [(item.source_anchor, item.review.state.value) for item in document.items]
    if carried:
        assert placed == [("body:0002", "review_complete"), ("body:0004", "review_complete")]
    else:
        assert placed == [
            ("body:0002", "review_required"),
            ("body:0004", "review_complete"),
        ], "a picture the reply did not place keeps the question's own source, picture included"
    assert document.items[0].body_asset_ids() == (asset_id,)
    assert outcome.update.pending == ()


@pytest.mark.asyncio
async def test_an_unlabelable_question_does_not_start_the_converting_phase_before_labeling():
    """A question no labeler sees converts at once, but the phase stays on sorting until the
    first labeled batch (TASK-SKRIPT-39-04-23): the count must not sit at 0 under sorting."""
    progress = RecordingProgress()
    await convert(table_exam(), GROUPING, progress=progress)

    trace = progress.trace
    assert progress.phases == [
        ConversionPhase.FINDING,
        ConversionPhase.SORTING,
        ConversionPhase.CONVERTING,
    ]
    assert trace.index("phase:converting") > trace.index("door:decisions")
