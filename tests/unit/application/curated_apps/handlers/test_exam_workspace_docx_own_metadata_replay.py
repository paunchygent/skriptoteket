"""A question's own chunk a reply lists as an instruction or the title stands only at its question
(D42); one an item of the reply also lists stays with that item.

Each fixture holds unedited live replies (see its README). An instruction placed in its
question's body, or on a parent holding the question, stands as placed. One that would land
anywhere else is no instruction: its chunk goes back to the question, which stays converted. The
check mark shows the chunk as printed only when the item lacks its wording (D41, D4); a parsing
issue never blocks export (D1).
"""

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.docx_own_instructions import (
    LEFT_OUT_REASON,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamItemKind,
    NativeItemReviewState,
    NativeParseOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_export_rules import (
    native_export_blockers,
)
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import (
    FIXTURES,
    RECORDINGS,
    SecondWaveByAnchor,
    build_replay,
    corpus_chunks,
    recording,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

_ROOT = FIXTURES / "docx_build_v16_low21_own_heading_metadata"
_EXAM = "svenska_2_kursavslutande_prov_med_facit"


async def test_an_own_heading_a_reply_lists_as_an_instruction_stays_in_the_check_mark():
    questions = recording(_EXAM, "docx_grouping_1", root=_ROOT)["questions"]
    assert isinstance(questions, list)
    (question,) = [q for q in questions if isinstance(q, dict) and q["id"] == "q19"]
    assert question["anchors"] == ["body:0079", "body:0081"]
    reply = recording(_EXAM, "docx_w2-07-01", root=_ROOT)
    instructions, items = reply["instructions"], reply["items"]
    assert isinstance(instructions, list) and isinstance(instructions[0], dict)
    assert instructions[0]["source_anchors"] == ["body:0079"]
    assert isinstance(items, list) and isinstance(items[0], dict)
    assert items[0]["source_anchors"] == ["body:0081", "body:0082"]

    provider = SecondWaveByAnchor(_EXAM, root=_ROOT)
    replay = build_replay(_EXAM, root=_ROOT, families_per_batch=1, provider=provider)
    outcome = await replay.pipeline.convert(job=replay.job())

    document = outcome.result.document
    heading = {c.anchor: c.text for c in corpus_chunks(_EXAM)}["body:0079"]
    assert heading == "Fråga 19. Satsdelar"
    (item_id,) = outcome.update.item_ids["q19"]
    (item,) = [i for i in document.items if i.item_id == item_id]
    assert item.kind is NativeExamItemKind.GAP_FILL
    assert item.review.parse_origin is NativeParseOrigin.LLM_PARSED
    # The item lacks the heading's wording, so the check mark shows it as printed (D4).
    assert item.review.state is NativeItemReviewState.REVIEW_REQUIRED
    assert item.review.reasons[-2:] == (LEFT_OUT_REASON, heading)
    assert heading not in document.instructions
    assert all(b.item_id != item.item_id for b in native_export_blockers(document))


async def test_an_own_lead_in_a_reply_lists_as_an_instruction_stands_on_the_parent_it_opens():
    exam = "chapter_4_poetry_and_lyrics_quiz_med_facit"
    questions = recording(exam, "docx_grouping_1")["questions"]
    assert isinstance(questions, list)
    (question,) = [q for q in questions if isinstance(q, dict) and q["id"] == "q5"]
    assert question["anchors"] == ["body:0018", "body:0019", "body:0020"]
    reply = recording(exam, "docx_w1-01")
    instructions = reply["instructions"]
    assert isinstance(instructions, list)
    assert any(isinstance(i, dict) and i["source_anchors"] == ["body:0018"] for i in instructions)

    replay = build_replay(exam, root=RECORDINGS)
    outcome = await replay.pipeline.convert(job=replay.job())

    document = outcome.result.document
    lead_in = {c.anchor: c.text for c in corpus_chunks(exam)}["body:0018"]
    assert lead_in == "Read the sentence:"
    (q5,) = outcome.update.item_ids["q5"]
    (q6,) = outcome.update.item_ids["q6"]
    (parent,) = [p for p in document.parents if lead_in in p.instruction]
    assert parent.item_ids == (q5, q6)
    for item in (i for i in document.items if i.item_id in (q5, q6)):
        assert lead_in not in item.plain_text_lines()
        assert LEFT_OUT_REASON not in item.review.reasons
        assert item.review.state is NativeItemReviewState.REVIEW_COMPLETE
    assert lead_in not in document.instructions
    assert native_export_blockers(document) == ()


async def test_an_own_line_a_reply_lists_as_an_instruction_stands_at_its_place_in_the_item():
    exam = "svenska_2_grammatik_omprov_variant_1_med_facit"
    root = FIXTURES / "docx_build_low16_own_instruction"
    questions = recording(exam, "docx_grouping_1", root=root)["questions"]
    assert isinstance(questions, list)
    (question,) = [q for q in questions if isinstance(q, dict) and q["id"] == "q2"]
    assert question["anchors"] == ["body:0016", "body:0017"]
    reply = recording(exam, "docx_w2-01-01", root=root)
    instructions, items = reply["instructions"], reply["items"]
    assert isinstance(instructions, list) and isinstance(instructions[0], dict)
    assert instructions[0]["source_anchors"] == ["body:0017"]
    assert isinstance(items, list) and isinstance(items[0], dict)
    listed = items[0]["source_anchors"]
    assert isinstance(listed, list) and "body:0017" not in listed

    provider = SecondWaveByAnchor(exam, root=root)
    replay = build_replay(exam, root=root, families_per_batch=1, provider=provider)
    outcome = await replay.pipeline.convert(job=replay.job())

    document = outcome.result.document
    line = {c.anchor: c.text for c in corpus_chunks(exam)}["body:0017"]
    assert line == "Skriv NF, PF eller VF."
    assert outcome.update.item_ids["q2"] == ("item_002",)
    (item,) = [i for i in document.items if i.item_id == "item_002"]
    assert item.review.parse_origin is NativeParseOrigin.LLM_PARSED
    # The question's printed heading opens the body (T1, 39-05-08); the line stands
    # between it and the first part, as in the source.
    lines = item.plain_text_lines()
    assert lines[0] == "Ange frastyp."
    assert lines[1] == line
    assert lines[2].startswith("a) De trötta eleverna")
    assert LEFT_OUT_REASON not in item.review.reasons
    assert item.review.state is NativeItemReviewState.REVIEW_COMPLETE
    assert line not in document.instructions
