"""Fråga 1 of the svenska_2 grammar replays goes to review (TASK-SKRIPT-39-04-17).

Its source paragraphs carry an inline answer key (``Svar:``) with no blank run
before it, so each a)-c) paragraph builds one blank run at the label's place.
The converter reply instead splits the word into morphemes with one gap per
class, so the gap count differs and admission records ``gap_count_mismatch``:
the item shows its source text for review, never the reply's morpheme split.
"""

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeItemReviewState,
    NativeParseOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_plain_text
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import build_replay

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]


@pytest.mark.parametrize(
    ("exam", "word", "reply_split"),
    [
        (
            "svenska_2_grammatik_omprov_variant_1_med_facit",
            "snöbollarnas",
            "snö + boll",
        ),
        (
            "svenska_2_grammatik_omprov_variant_2_med_facit",
            "solrosornas",
            "sol + ros",
        ),
    ],
)
async def test_fraga_1_with_an_inline_answer_key_goes_to_review(
    exam: str, word: str, reply_split: str
):
    replay = build_replay(exam)
    outcome = await replay.pipeline.convert(job=replay.job())
    item = next(item for item in outcome.update.document.items if item.printed_label == "Fråga 1")
    assert item.review.state is NativeItemReviewState.REVIEW_REQUIRED
    assert item.review.parse_origin is NativeParseOrigin.SOURCE_FALLBACK
    assert "Frågan följer inte provformatet: 5 luckor men 1 svarsplats." in item.review.reasons
    mismatches = [event for event in outcome.result.events if event.code == "gap_count_mismatch"]
    assert [event.detail for event in mismatches] == ["5 gaps for 1 blank runs"]
    text = body_plain_text(item.body)
    assert word in text
    assert reply_split not in text
    assert "[___]" not in text
    assert "Svar:" not in text
    assert "(R)" not in text
    assert "(A)" not in text
    assert "(B)" not in text
