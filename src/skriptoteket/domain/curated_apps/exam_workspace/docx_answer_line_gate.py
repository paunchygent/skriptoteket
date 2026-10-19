"""The one W10 gate for an imported item left with no body but answer lines.

Purpose:
    Printed answer lines are answer space, not question text: the final gate
    drops them from an item body without ever editing, merging or rewriting a
    kept paragraph. An item whose gated body is empty has no question left, so
    it goes to teacher review with ``ANSWER_LINE_ONLY_REASON``. The gate also
    covers the item an earlier W10 site already emptied: when the item's own
    source chunk is itself only an answer line, the empty body still goes to
    review instead of staying complete.

Relationships:
    - Called by ``docx_ai_build.assemble_build_result`` for every item, after
      every rebuild path, next to the gate's caller rather than in the body leaf.
    - Called by ``exam_workspace_docx_retry`` for every single-question retry item,
      which never reaches ``assemble_build_result``.
    - Reads answer-line detection and body gating from ``shared_body``, which
      stays a body-only leaf; item review logic lives here, not there.
    - Appends its reason once to the existing reasons through ``model_copy``,
      the way ``docx_own_instructions.with_left_out_mark`` does; gaps, pictures
      and the source anchor are never changed.
"""

from __future__ import annotations

from collections.abc import Mapping

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import (
    DocxChunk,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
    NativeExamItem,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeItemReviewState,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import (
    is_answer_line_chunk,
    without_printed_answer_lines,
)

ANSWER_LINE_ONLY_REASON = "Frågan innehöll bara skrivlinjer i källan – kontrollera mot källan."


def gated_item(item: NativeExamItem, by_anchor: Mapping[str, DocxChunk]) -> NativeExamItem:
    """The item without printed answer-line paragraphs, reviewed when emptied (W10).

    Paragraphs are only removed, never edited. An item whose gated body is empty
    goes to teacher review with ``ANSWER_LINE_ONLY_REASON`` appended once to its
    existing reasons, when either the gate itself removed a paragraph or the
    item's source chunk (looked up by ``source_anchor`` in ``by_anchor``) is
    itself only an answer line. An item that keeps every paragraph is returned
    untouched, and so is an item whose body was already empty from a source that
    is not an answer-line chunk.
    """
    kept = without_printed_answer_lines(item.body)
    if kept:
        if len(kept) == len(item.body):
            return item
        return item.model_copy(update={"body": kept})
    removed = len(item.body) > 0
    chunk = None if item.source_anchor is None else by_anchor.get(item.source_anchor)
    if not (removed or (chunk is not None and is_answer_line_chunk(chunk))):
        return item
    reasons = tuple(dict.fromkeys((*item.review.reasons, ANSWER_LINE_ONLY_REASON)))
    review = item.review.model_copy(
        update={"state": NativeItemReviewState.REVIEW_REQUIRED, "reasons": reasons}
    )
    return item.model_copy(update={"body": kept, "review": review})
