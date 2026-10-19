"""A converted item holds the own chunks of its question that the reply leaves out.

This module owns the left-out own-chunk check at admission (D41, TASK-SKRIPT-39-04-14 D4,
TASK-SKRIPT-39-04-15 D1-D2): chunks the reply lists or leaves unlisted that no body
paragraph, choice or matching entry is aligned to are held under the item's check mark as
printed, except source answers, facit lines, points lines, grouped keys, governing chunks,
headers and section-placed instructions. Admission records the anchors the item leaves
out; the check mark itself is decided later, on the placed item (TASK-SKRIPT-39-04-19).
"""

from dataclasses import replace

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_admit_metadata import (
    is_points_line,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_state import (
    DocxBuildState,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_item_alignment import (
    AcceptedEntry,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_own_instructions import (
    left_out_chunks,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeParseOrigin,
)


def with_left_out(
    index: int,
    admitted: AcceptedEntry,
    state: DocxBuildState,
    seen: set[str],
    item_held: frozenset[str],
) -> AcceptedEntry:
    """A converted item holds the own chunks of its question it leaves out; those no body
    paragraph, choice or matching entry is aligned to show under a check mark as printed, a
    possible parsing issue (D41, D4).

    The check also covers every own chunk of the question the item itself lists, so a listed
    chunk the item shows nothing of is marked too (TASK-SKRIPT-39-04-15 D1). A listed chunk
    is never marked when it is a source answer or facit line, a points line, a grouped key, a
    governing chunk, a header or a section-placed instruction (D2); the alignment says what
    the item shows, never the reply's wording.

    A left-out chunk is an own chunk of a question the item touches that no entry holds yet
    and no item of the reply lists, except as a points line alone (D2). The anchors the
    item leaves out are recorded on the item; the check mark is decided on the placed item
    (TASK-SKRIPT-39-04-19).
    """
    aligned, anchors = admitted
    item = aligned.item
    if item.review.parse_origin is not NativeParseOrigin.LLM_PARSED:
        return admitted
    own = set().union(*(state.question_by_anchor.get(a, ()) for a in anchors))
    listed = tuple(
        a
        for a in anchors
        if a in own
        and a not in state.grouped_keys
        and a not in state.key_anchors
        and a not in state.governing
        and a not in state.header_anchors
        and a not in state.context_anchors
        and all(a not in m.source_anchors for m in state.instructions)
        and not is_points_line(a, state)
    )
    left_out = tuple(
        c.anchor
        for c in state.pending
        if c.anchor in own
        and c.anchor not in seen
        # A points line another entry lists alone is no item; this one holds it (D2).
        and (c.anchor not in item_held or is_points_line(c.anchor, state))
    )
    # A left-out chunk the grouping lists as the question's facit is its answer key.
    keys = {a for a in left_out if a in state.grouped_keys}
    state.key_anchors.update(keys)
    seen.update(keys)
    # A left-out points line is held without a mark: the item already read its points (D2).
    held = {a for a in left_out if a not in keys and is_points_line(a, state)}
    seen.update(held)
    anchors = (*anchors, *(a for a in left_out if a in held))
    left_out = tuple(a for a in left_out if a not in keys and a not in held)
    if not left_out and not listed:
        return aligned, anchors
    seen.update(left_out)
    # Both the left-out and the listed chunks are checked against the alignment; a chunk of
    # either the body shows or an entry is aligned to is not missing. Listed anchors are
    # already held, so only the left-out ones join ``seen`` and the returned anchors.
    examined = {*left_out, *listed}
    missing = left_out_chunks(aligned, (c for c in state.chunks if c.anchor in examined))
    if missing:
        moved = tuple(c.anchor for c in missing)
        state.record("admission", "own_chunks_left_out", item=index, anchors=moved)
        aligned = replace(aligned, left_out=aligned.left_out | {c.anchor for c in missing})
    return aligned, (*anchors, *left_out)
