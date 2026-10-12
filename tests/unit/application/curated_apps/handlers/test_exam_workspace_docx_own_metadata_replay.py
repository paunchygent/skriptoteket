"""A question's own chunk a reply lists only as metadata stays with its question.

``docx_build_v16_low21_own_heading_metadata`` holds unedited live replies of a
one-family-per-batch run (see its README). The grouping decides ownership: the heading the reply
lists as an instruction is no exam-wide instruction. The question stays converted and shows the
heading as printed in its check mark (D41), which blocks export until the teacher handles it.
"""

import pytest

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_admission import (
    LEFT_OUT_REASON,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamItemKind,
    NativeExportBlocker,
    NativeItemReviewState,
    NativeParseOrigin,
    native_export_blockers,
)
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import (
    FIXTURES,
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
    assert item.review.state is NativeItemReviewState.REVIEW_REQUIRED
    assert item.review.reasons[-2:] == (LEFT_OUT_REASON, heading)
    assert heading not in document.instructions
    blocker = NativeExportBlocker(item_id=item.item_id, reason="review_required")
    assert blocker in native_export_blockers(document)
