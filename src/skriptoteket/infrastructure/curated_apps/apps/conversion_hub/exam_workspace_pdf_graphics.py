"""Find pictures and drawn figures on one PDF page from pure box geometry.

Purpose: turn one page's placed pictures, vector strokes, word boxes, visual
lines and ruled-table boxes into cut regions (pictures and figures) with their
label words, using only deterministic box predicates. No text is inspected.

Rules:
    A figure owns the words whose centre lies inside its drawn outline grown by
    ``_LABEL_INSIDE_POINTS``, plus the label runs in one ring around it. Each visual
    line splits into runs at every horizontal gap between neighbouring words of at
    least ``_RUN_GAP_RATIO`` body sizes; a run is the unit of label ownership. A run
    with some words inside the grown hull and some outside gives none of its words;
    a ring run lies outside the hull, within ``_LABEL_SIDE_RATIO`` body sizes sideways
    and ``_LABEL_VERTICAL_RATIO`` body sizes above or below, wholly within the side
    reach, and never starts at the left text margin (its first word). A word claimed
    by more than one cut goes to the cut whose hull is nearest its run box
    (horizontal gap plus vertical gap, 0 when overlapping); ties break by hull-centre
    distance to the word centre, then the smaller hull top, then the smaller hull
    left. The cut box covers the hull and the cut's own resolved labels, grown by the
    margin and stopped short of every non-label word. A cluster without images
    whose strokes all lie on the hull boundary is an outline-only figure: it owns
    no words inside it, but takes ring labels such as a dimension below it. Such a
    box holding a margin-starting line is a paragraph or page border (no cut), and
    a ``rect`` stroke holding one is dropped before clustering. A placed picture of
    any size is a picture cut. An axis title one ring further out is read as text.

Relationships:
    The layout adapter builds ``PageGraphics`` from pdfplumber page objects;
    the chunker renders each returned ``PdfCut`` to PNG. This module imports
    nothing from pdfplumber, pypdfium2 or the layout module.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import hypot
from typing import Literal

Box = tuple[float, float, float, float]  # x0, top, x1, bottom in points, page top-left origin


@dataclass(frozen=True)
class PdfStroke:
    """One vector path on the page: a straight line, a rectangle or any other path."""

    box: Box
    kind: Literal["line", "rect", "curve"]
    stroked: bool  # draws a visible (non-white) outline
    filled: bool  # draws a visible (non-white) fill


@dataclass(frozen=True)
class PageGraphics:
    """One page's geometry: pictures, strokes, word boxes, visual lines, tables."""

    width: float
    height: float
    images: tuple[Box, ...]  # placed pictures
    strokes: tuple[PdfStroke, ...]
    words: tuple[Box, ...]  # every word on the page
    lines: tuple[tuple[int, ...], ...]  # visual lines: indices into ``words``, left to right
    tables: tuple[Box, ...]  # ruled tables that hold text
    text_left: float  # the document's left text margin, where body lines start


@dataclass(frozen=True)
class PdfCut:
    """One region to cut out of the rendered page, with its label word indices."""

    kind: Literal["picture", "figure"]
    box: Box  # the region to cut out of the rendered page
    labels: frozenset[int]  # indices into ``words`` that belong to the cut


_THIN_POINTS = 2.0  # a stroke at most this thick reads as a thin rule
_TABLE_SLACK_POINTS = 2.0  # table boxes grow this far when swallowing their rules
_JOIN_RATIO = 0.5  # each graphic grows this many body sizes per side before joining
_LABEL_INSIDE_POINTS = 1.0  # the hull grows this far when catching inside labels
# A label line beside the drawing: at most this many body sizes away from the hull
# sideways, and wholly within that reach left and right of it.
_LABEL_SIDE_RATIO = 1.5
# A label line above or below the drawing: at most this many body sizes of white space
# from the hull. Body text after a figure usually sits further off; an axis title one
# ring further out is read as text, a duplicate the teacher can delete.
_LABEL_VERTICAL_RATIO = 0.5
# A line starting this close to the document's left text margin is body text, never a
# ring label: paragraphs start there, a figure's labels sit by the drawing. When such
# a line reaches into a boundary box the box is a paragraph or page border, never a
# figure.
_MARGIN_START_POINTS = 1.0
# A visual line splits into label runs at every horizontal gap between neighbouring
# words of at least this many body sizes (word spaces are far smaller).
_RUN_GAP_RATIO = 1.0
_MARGIN_RATIO = 1.0  # a figure cut grows this many body sizes past hull and labels
_WORD_CLEARANCE_POINTS = 1.0  # a figure margin stops this short of neighbouring words


def _centre(box: Box) -> tuple[float, float]:
    return ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2)


def _grown(box: Box, amount: float) -> Box:
    return (box[0] - amount, box[1] - amount, box[2] + amount, box[3] + amount)


def _intersects(first: Box, second: Box) -> bool:
    return (
        first[0] <= second[2]
        and second[0] <= first[2]
        and first[1] <= second[3]
        and second[1] <= first[3]
    )


def _union(boxes: tuple[Box, ...]) -> Box:
    return (
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    )


def _centre_inside(box: Box, outer: Box) -> bool:
    x, y = _centre(box)
    return outer[0] <= x <= outer[2] and outer[1] <= y <= outer[3]


def _line_starts_at_margin(graphics: PageGraphics, line: tuple[int, ...]) -> bool:
    """A visual line whose first word starts at the document's left text margin."""
    if not line:
        return False
    first = line[0]
    if not 0 <= first < len(graphics.words):
        return False
    return abs(graphics.words[first][0] - graphics.text_left) <= _MARGIN_START_POINTS


def _box_holds_margin_line(graphics: PageGraphics, box: Box) -> bool:
    """A margin-starting line with a word centre inside the box: a border, not a figure."""
    for line in graphics.lines:
        if not _line_starts_at_margin(graphics, line):
            continue
        if any(
            0 <= index < len(graphics.words) and _centre_inside(graphics.words[index], box)
            for index in line
        ):
            return True
    return False


def _kept_strokes(graphics: PageGraphics) -> tuple[PdfStroke, ...]:
    """Strokes that can start a cut; shading, table rules and borders are out."""
    grown_tables = tuple(_grown(box, _TABLE_SLACK_POINTS) for box in graphics.tables)
    kept: list[PdfStroke] = []
    for stroke in graphics.strokes:
        if not stroke.stroked and not stroke.filled:
            continue
        centre = _centre(stroke.box)
        if any(
            box[0] <= centre[0] <= box[2] and box[1] <= centre[1] <= box[3] for box in grown_tables
        ):
            continue
        if stroke.kind == "rect" and _box_holds_margin_line(graphics, stroke.box):
            continue
        if (
            stroke.kind == "rect"
            and stroke.filled
            and not stroke.stroked
            and any(_centre_inside(word, stroke.box) for word in graphics.words)
        ):
            continue
        kept.append(stroke)
    return tuple(kept)


def _clusters(
    strokes: tuple[PdfStroke, ...], images: tuple[Box, ...], join: float
) -> list[tuple[tuple[PdfStroke, ...], tuple[Box, ...]]]:
    """Group strokes and images whose join-grown boxes intersect (union-find)."""
    boxes: list[Box] = [*[stroke.box for stroke in strokes], *images]
    grown = [_grown(box, join) for box in boxes]
    parent = list(range(len(boxes)))
    for first in range(len(boxes)):
        for second in range(first + 1, len(boxes)):
            if _intersects(grown[first], grown[second]):
                root_first, root_second = first, second
                while parent[root_first] != root_first:
                    root_first = parent[root_first]
                while parent[root_second] != root_second:
                    root_second = parent[root_second]
                if root_first != root_second:
                    parent[root_second] = root_first
    groups: dict[int, list[int]] = {}
    for index in range(len(boxes)):
        root = index
        while parent[root] != root:
            root = parent[root]
        groups.setdefault(root, []).append(index)
    stroke_count = len(strokes)
    result: list[tuple[tuple[PdfStroke, ...], tuple[Box, ...]]] = []
    for members in groups.values():
        member_strokes = tuple(strokes[i] for i in members if i < stroke_count)
        member_images = tuple(images[i - stroke_count] for i in members if i >= stroke_count)
        result.append((member_strokes, member_images))
    return result


def _is_horizontal_thin(box: Box) -> bool:
    return box[3] - box[1] <= _THIN_POINTS


def _is_vertical_thin(box: Box) -> bool:
    return box[2] - box[0] <= _THIN_POINTS


def _on_boundary(stroke: PdfStroke, hull: Box) -> bool:
    """A rect matching the hull, or a thin line/rect lying along one hull edge."""
    box = stroke.box
    if stroke.kind == "rect" and all(
        abs(edge - edge_hull) <= _THIN_POINTS for edge, edge_hull in zip(box, hull, strict=True)
    ):
        return True
    if stroke.kind not in ("line", "rect"):
        return False
    if _is_horizontal_thin(box):
        near_top = box[0] >= hull[0] - _THIN_POINTS and box[2] <= hull[2] + _THIN_POINTS
        along_top = box[1] <= hull[1] + _THIN_POINTS and box[3] >= hull[1] - _THIN_POINTS
        along_bottom = box[1] <= hull[3] + _THIN_POINTS and box[3] >= hull[3] - _THIN_POINTS
        return near_top and (along_top or along_bottom)
    if _is_vertical_thin(box):
        near_side = box[1] >= hull[1] - _THIN_POINTS and box[3] <= hull[3] + _THIN_POINTS
        along_left = box[0] <= hull[0] + _THIN_POINTS and box[2] >= hull[0] - _THIN_POINTS
        along_right = box[0] <= hull[2] + _THIN_POINTS and box[2] >= hull[2] - _THIN_POINTS
        return near_side and (along_left or along_right)
    return False


def _label_runs(
    graphics: PageGraphics, line: tuple[int, ...], body_size: float
) -> list[tuple[int, ...]]:
    """One visual line split into runs at every wide horizontal word gap.

    Neighbouring words left to right form one run until the gap between them is at
    least ``_RUN_GAP_RATIO`` body sizes; a run is the unit of label ownership.
    """
    members = [index for index in line if 0 <= index < len(graphics.words)]
    if not members:
        return []
    ordered = sorted(members, key=lambda index: graphics.words[index][0])
    threshold = _RUN_GAP_RATIO * body_size
    runs: list[list[int]] = [[ordered[0]]]
    for previous, current in zip(ordered, ordered[1:]):
        if graphics.words[current][0] - graphics.words[previous][2] >= threshold:
            runs.append([current])
        else:
            runs[-1].append(current)
    return [tuple(run) for run in runs]


def _figure_labels(
    graphics: PageGraphics,
    runs: tuple[tuple[int, ...], ...],
    hull: Box,
    grown_hull: Box,
    body_size: float,
) -> frozenset[int]:
    """Hull-inside words plus the label runs in the ring around the hull, one ring.

    A ring run lies outside the hull, within ``_LABEL_SIDE_RATIO`` body sizes of it
    sideways and ``_LABEL_VERTICAL_RATIO`` body sizes above or below, and wholly within
    the side reach left and right, so a wrapped text line beside the figure is no label.
    A run starting at the left text margin (its first word) is a paragraph, never a
    ring label. A run with some words inside the grown hull and some outside gives
    none of its words: the run stays text.
    """
    side = _LABEL_SIDE_RATIO * body_size
    vertical = _LABEL_VERTICAL_RATIO * body_size
    labels = {
        index for index, word in enumerate(graphics.words) if _centre_inside(word, grown_hull)
    }
    for run in runs:
        inside = [index for index in run if index in labels]
        if inside:
            if len(inside) != len(run):
                labels.difference_update(inside)
            continue
        box = _union(tuple(graphics.words[index] for index in run))
        horizontal_gap = max(0.0, box[0] - hull[2], hull[0] - box[2])
        vertical_gap = max(0.0, box[1] - hull[3], hull[1] - box[3])
        within_reach = box[0] >= hull[0] - side and box[2] <= hull[2] + side
        at_margin = abs(box[0] - graphics.text_left) <= _MARGIN_START_POINTS
        in_ring = horizontal_gap <= side and vertical_gap <= vertical
        if in_ring and within_reach and not at_margin:
            labels.update(run)
    return frozenset(labels)


def _figure_box(
    union: Box, graphics: PageGraphics, labels: frozenset[int], body_size: float
) -> Box:
    """The union grown by the margin, shrunk short of neighbours, clamped to the page."""
    margin = _MARGIN_RATIO * body_size
    grown = _grown(union, margin)
    left, top, right, bottom = grown
    others = [word for index, word in enumerate(graphics.words) if index not in labels]

    def overlaps(vertical: bool, low: float, high: float, word: Box) -> bool:
        span = (word[1], word[3]) if vertical else (word[0], word[2])
        return span[0] < high and span[1] > low

    # Each side stops short of the nearest non-label word the grown box would cover:
    # a side yields only to a word beside it, overlapping the union on the other axis.
    left_edge = left
    for word in others:
        if overlaps(True, union[1], union[3], word) and word[0] < union[0] and word[2] > left:
            left_edge = max(left_edge, word[2] + _WORD_CLEARANCE_POINTS)
    left = min(left_edge, union[0])
    right_edge = right
    for word in others:
        if overlaps(True, union[1], union[3], word) and word[2] > union[2] and word[0] < right:
            right_edge = min(right_edge, word[0] - _WORD_CLEARANCE_POINTS)
    right = max(right_edge, union[2])
    top_edge = top
    for word in others:
        if overlaps(False, union[0], union[2], word) and word[1] < union[1] and word[3] > top:
            top_edge = max(top_edge, word[3] + _WORD_CLEARANCE_POINTS)
    top = min(top_edge, union[1])
    bottom_edge = bottom
    for word in others:
        if overlaps(False, union[0], union[2], word) and word[3] > union[3] and word[1] < bottom:
            bottom_edge = min(bottom_edge, word[1] - _WORD_CLEARANCE_POINTS)
    bottom = max(bottom_edge, union[3])
    return (
        min(max(left, 0.0), graphics.width),
        min(max(top, 0.0), graphics.height),
        min(max(right, 0.0), graphics.width),
        min(max(bottom, 0.0), graphics.height),
    )


def _nearest_owner(
    graphics: PageGraphics,
    run_box: dict[int, Box],
    word: int,
    hulls: list[Box],
) -> int:
    """Index into ``hulls`` of the cut owning ``word``: nearest hull to its run box.

    Distance is the horizontal gap plus the vertical gap between the hull and the
    word's run box (0 when they overlap). Ties break by hull-centre distance to the
    word centre, then the smaller hull top, then the smaller hull left.
    """
    box = run_box.get(word, graphics.words[word])
    centre = _centre(graphics.words[word])
    best = 0
    best_key: tuple[float, float, float, float] | None = None
    for position, hull in enumerate(hulls):
        horizontal_gap = max(0.0, box[0] - hull[2], hull[0] - box[2])
        vertical_gap = max(0.0, box[1] - hull[3], hull[1] - box[3])
        hull_centre = _centre(hull)
        key = (
            horizontal_gap + vertical_gap,
            hypot(centre[0] - hull_centre[0], centre[1] - hull_centre[1]),
            hull[1],
            hull[0],
        )
        if best_key is None or key < best_key:
            best = position
            best_key = key
    return best


def _run_boxes(graphics: PageGraphics, runs: tuple[tuple[int, ...], ...]) -> dict[int, Box]:
    """Each word's run box: the union of the run it belongs to."""
    boxes: dict[int, Box] = {}
    for run in runs:
        box = _union(tuple(graphics.words[index] for index in run))
        for index in run:
            boxes[index] = box
    return boxes


def _picture_labels(graphics: PageGraphics, hull: Box) -> frozenset[int]:
    """Words printed on a picture, or none when the picture lies behind a paragraph.

    A visual line that reaches into the picture from the left text margin is a paragraph
    the picture sits behind; its text stays text, so the picture claims no words.
    """
    inside = {index for index, word in enumerate(graphics.words) if _centre_inside(word, hull)}
    for line in graphics.lines:
        if any(index in inside for index in line) and any(
            abs(graphics.words[index][0] - graphics.text_left) <= _MARGIN_START_POINTS
            for index in line[:1]
        ):
            return frozenset()
    return frozenset(inside)


def page_cuts(graphics: PageGraphics, *, body_size: float) -> tuple[PdfCut, ...]:
    """Cut regions for one page's pictures and drawn figures, top to bottom then left.

    A placed picture of any size is a picture cut. A cluster without images whose
    strokes all lie on the hull boundary is an outline-only figure: it owns no words
    inside it, but takes ring labels such as a dimension below it, unless a
    margin-starting line reaches into it (a paragraph or page border, no cut).
    """
    strokes = _kept_strokes(graphics)
    images = tuple(graphics.images)
    join = _JOIN_RATIO * body_size
    grown_hull_slack = _LABEL_INSIDE_POINTS
    runs = tuple(run for line in graphics.lines for run in _label_runs(graphics, line, body_size))
    run_box = _run_boxes(graphics, runs)
    pending: list[tuple[Literal["picture", "figure"], Box, frozenset[int]]] = []
    for member_strokes, member_images in _clusters(strokes, images, join):
        members: tuple[Box, ...] = (
            *[stroke.box for stroke in member_strokes],
            *member_images,
        )
        hull = _union(members)
        width = hull[2] - hull[0]
        height = hull[3] - hull[1]
        outline_only = False
        if not member_images:
            if all(_is_horizontal_thin(stroke.box) for stroke in member_strokes):
                continue
            if all(_is_vertical_thin(stroke.box) for stroke in member_strokes):
                continue
            if width < body_size and height < body_size:
                continue
            if all(_on_boundary(stroke, hull) for stroke in member_strokes):
                if _box_holds_margin_line(graphics, hull):
                    continue
                outline_only = True
        elif all(_on_boundary(stroke, hull) for stroke in member_strokes):
            pending.append(("picture", hull, _picture_labels(graphics, hull)))
            continue
        grown_hull = _grown(hull, grown_hull_slack)
        labels = _figure_labels(graphics, runs, hull, grown_hull, body_size)
        if outline_only:
            labels = frozenset(
                index for index in labels if not _centre_inside(graphics.words[index], grown_hull)
            )
        pending.append(("figure", hull, labels))
    # One word, one owner, decided by geometry before any cut box is computed: a
    # word claimed by more than one cut goes to the nearest hull to its run box.
    claims: dict[int, list[int]] = {}
    for position, (_, _, labels) in enumerate(pending):
        for index in labels:
            claims.setdefault(index, []).append(position)
    owned = [set(labels) for _, _, labels in pending]
    for index, positions in claims.items():
        if len(positions) > 1:
            winner = positions[
                _nearest_owner(
                    graphics, run_box, index, [pending[position][1] for position in positions]
                )
            ]
            for position in positions:
                if position != winner:
                    owned[position].discard(index)
    cuts = []
    for (kind, hull, _), kept in zip(pending, owned):
        resolved = frozenset(kept)
        if kind == "picture":
            cuts.append(PdfCut(kind="picture", box=hull, labels=resolved))
        else:
            union = _union((hull, *[graphics.words[index] for index in resolved]))
            if not resolved:
                union = hull
            cuts.append(
                PdfCut(
                    kind="figure",
                    box=_figure_box(union, graphics, resolved, body_size),
                    labels=resolved,
                )
            )
    cuts.sort(key=lambda cut: (cut.box[1], cut.box[0]))
    return tuple(cuts)
