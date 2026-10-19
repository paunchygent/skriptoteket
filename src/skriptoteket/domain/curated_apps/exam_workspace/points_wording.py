"""Item orchestration for settled points wording.

When the shape matches but the number differs, the wording stays and
``leftover_points_wording`` reports it for the points-note offer; a terminal
heading reports a differing number for exactly the shapes its rule would
remove at an equal number, while a sentence or range ending records nothing.
``with_settled_points_wording`` settles each outcome on the final item. Only
the label's position and its number decide; the stem itself is never read or
rewritten.
"""

from __future__ import annotations

from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import POINT_LABEL
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeAssetSegment,
    NativeGapSegment,
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.points_wording_cuts import (
    body_keeps_text,
    body_without_first_paragraph_points,
    body_without_heading_points,
    body_without_trailing_points,
    heading_bare_label_cut,
    paragraph_keeping_run_text,
    trailing_run_wording,
)
from skriptoteket.domain.curated_apps.exam_workspace.points_wording_shapes import (
    HEADING_TRAILING_SEPARATOR,
    points_only_line_start,
)


def _heading_last_leftover(body: tuple[NativeParagraph, ...], points: int | float) -> str | None:
    """The wording a terminal heading would leave at an equal number, when it differs.

    One shape decision serves the cut and the recording: the shared run
    wording decides parenthesised and whole-line shapes, the latter cut by
    the head shape, while the bare-label cut decides separator-preceded bare
    labels; any other bare ending stays and records nothing. Survival is the
    removal's own rule: the kept run text plus the paragraph's earlier
    segments, so a question, gap or picture in the same paragraph keeps the
    body and the wording is recorded.
    """
    paragraph = body[-1]
    located = trailing_run_wording((paragraph,))
    if located is not None:
        run, run_text, found = located
        if found.value == points:
            return None
        start = points_only_line_start(run_text) if found.whole_line else found.start
        kept_text = run_text[:start].rstrip()
    else:
        bare = heading_bare_label_cut(paragraph)
        if bare is None:
            return None
        run, run_text, start, value = bare
        if value == points:
            return None
        kept_text = HEADING_TRAILING_SEPARATOR.sub("", run_text[:start].rstrip())
    settled_paragraph = paragraph_keeping_run_text(paragraph, run, kept_text)
    settled = (*body[:-1], settled_paragraph) if settled_paragraph is not None else body[:-1]
    if body_keeps_text(settled):
        return run_text[start:].strip()
    return None


def leftover_points_wording(
    body: tuple[NativeParagraph, ...], points: int | float | None
) -> str | None:
    """The trailing points wording whose number differs from the given points.

    The same run and shape check as the removal decides: an equal number, no
    settled points, and a wording that is the whole question text record
    nothing. A terminal heading records a differing number for exactly the
    shapes its rule would remove at an equal number. A bare label inside a
    sentence never matches, so it is never recorded.
    """
    if points is None:
        return None
    if body and body[-1].heading_level is not None:
        return _heading_last_leftover(body, points)
    located = trailing_run_wording(body)
    if located is None:
        return None
    run, run_text, found = located
    if found.value == points:
        return None
    paragraph = body[-1]
    kept_text = run_text[: found.start].rstrip()
    settled_paragraph = paragraph_keeping_run_text(paragraph, run, kept_text)
    settled = (*body[:-1], settled_paragraph) if settled_paragraph is not None else body[:-1]
    for kept_paragraph in settled:
        for placed in kept_paragraph.segments:
            if isinstance(placed, NativeTextSegment):
                if placed.text.strip():
                    return run_text[found.start :].strip()
            elif isinstance(placed, (NativeGapSegment, NativeAssetSegment)):
                return run_text[found.start :].strip()
    return None


def _body_label_count(body: tuple[NativeParagraph, ...]) -> int:
    """The points labels over the joined text of every paragraph's text segments."""
    joined = "\n".join(
        "".join(
            segment.text for segment in paragraph.segments if isinstance(segment, NativeTextSegment)
        )
        for paragraph in body
    )
    return len(list(POINT_LABEL.finditer(joined)))


def with_settled_points_wording(item: NativeExamItem) -> NativeExamItem:
    """The item with its trailing points wording settled against its points.

    An equal number leaves the wording from the body's end (never from a
    heading last paragraph), then from its first paragraph, then from any
    heading paragraph; a heading never loses its own words. A differing
    number at the non-heading end keeps the wording and records
    it in ``leftover_points_text`` for the points-note offer, as does a
    differing number at a terminal heading for exactly the shapes its rule
    would remove; a differing first-paragraph or non-terminal heading number
    records nothing. Only the body and the leftover field
    change; points, review and every source record stay as they are. A missing
    number, a stem of only wording or a body the rule never matches returns the
    item untouched. A body holding several labels is left untouched as well:
    nothing is removed and nothing is recorded.
    """
    if _body_label_count(item.body) > 1:
        return item
    settled = body_without_trailing_points(item.body, item.points)
    if settled == item.body:
        leftover = leftover_points_wording(item.body, item.points)
        if leftover is not None:
            return item.model_copy(update={"leftover_points_text": leftover})
        settled = body_without_first_paragraph_points(item.body, item.points)
    else:
        settled = body_without_first_paragraph_points(settled, item.points)
    if settled != item.body:
        return item.model_copy(update={"body": settled})
    settled = body_without_heading_points(item.body, item.points)
    if settled != item.body:
        return item.model_copy(update={"body": settled})
    return item
