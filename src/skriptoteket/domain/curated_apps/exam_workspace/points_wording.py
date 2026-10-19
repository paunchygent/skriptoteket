"""Trailing points wording at the end of a native exam item body.

Printed points wording ("(1 point)", "Poäng: 6 poäng") states the item's
points, never its text: ``trailing_points`` finds such wording at the end of
a text. When its number equals the item's points, ``body_without_trailing_points``
drops it from the last paragraph of a non-heading body (keeping the word of a
whole-text one-word line, D13), and ``body_without_first_paragraph_points``
drops a parenthesised label ending the first paragraph or a first paragraph
that is only points wording; a points-only line is cut by its head shape,
which decides bare and parenthesised labels alike: an empty or colon head
leaves whole, a one-word head without a colon keeps its word (D12
Correction). ``body_without_heading_points`` drops an equal label ending a
heading paragraph anywhere in the body only as a parenthesised label, as a
bare label a dash or colon precedes, or as a whole points-only line cut by the
same head shape; any other bare label in a heading stays, so a sentence or
range ending never loses words. A heading last paragraph is never the
end-of-body rule's case. When the shape matches
but the number differs, the wording stays and ``leftover_points_wording``
reports it for the points-note offer; a terminal heading reports a differing
number for exactly the shapes its rule would remove at an equal number, while
a sentence or range ending records nothing. ``with_settled_points_wording`` settles
each outcome on the final item. Only the label's position and its number
decide; the stem itself is never read or rewritten.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import (
    POINT_LABEL,
    label_points,
    points_only_line,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeAssetSegment,
    NativeGapSegment,
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem


@dataclass(frozen=True)
class TrailingPoints:
    """Points wording at the end of a text: where it starts, its number, and shape."""

    start: int
    value: int | float
    # True for the points-line shape: a last line that is only a points line.
    whole_line: bool


def trailing_points(text: str) -> TrailingPoints | None:
    """Points wording at the end of a text, or None when the end holds prose.

    Two shapes count: a last line that is only a points line, which leaves
    with its newline, and a parenthesised label ending the last line, which
    leaves with the blank space before it. A label with no number is ignored.
    When the line holds several labels, nothing counts.
    """
    stripped = text.rstrip()
    line_start = stripped.rfind("\n") + 1
    line = stripped[line_start:]
    matches = list(POINT_LABEL.finditer(line))
    if not matches:
        return None
    if len(matches) > 1:
        return None
    if points_only_line(line):
        value = label_points(matches[0].group())
        if value is None:
            return None
        return TrailingPoints(
            start=line_start - 1 if line_start else 0, value=value, whole_line=True
        )
    last = matches[-1]
    if not last.group().startswith("(") or line[last.end() :].strip(" \t"):
        return None
    value = label_points(last.group())
    if value is None:
        return None
    start = line_start + last.start()
    while start > line_start and stripped[start - 1] in " \t":
        start -= 1
    return TrailingPoints(start=start, value=value, whole_line=False)


def without_trailing_points(text: str, points: int | float | None) -> str:
    """The text without trailing points wording that equals the given points.

    A differing number, missing points and a text of only wording keep the
    text unchanged: there is nothing to settle, or nothing would remain.
    """
    if points is None:
        return text
    found = trailing_points(text)
    if found is None or found.value != points:
        return text
    kept = text[: found.start].rstrip()
    if not kept.strip():
        return text
    return kept


def _trailing_text_run(
    paragraph: NativeParagraph,
) -> tuple[list[NativeTextSegment], str] | None:
    """The paragraph's trailing run of text segments and its joined text."""
    if not paragraph.segments or not isinstance(paragraph.segments[-1], NativeTextSegment):
        return None
    run: list[NativeTextSegment] = []
    for segment in reversed(paragraph.segments):
        if not isinstance(segment, NativeTextSegment):
            break
        run.append(segment)
    run.reverse()
    return (run, "".join(segment.text for segment in run))


def _trailing_run_wording(
    body: tuple[NativeParagraph, ...],
) -> tuple[list[NativeTextSegment], str, TrailingPoints] | None:
    """The last paragraph's trailing text run and its points wording, if any.

    Every guard sits here once: the paragraph ends in text, the run's wording is
    found, and a whole points line counts only when its line starts inside the
    run (the run holds a newline before the line, or the run is the paragraph).
    """
    if not body:
        return None
    paragraph = body[-1]
    located = _trailing_text_run(paragraph)
    if located is None:
        return None
    run, run_text = located
    found = trailing_points(run_text)
    if found is None:
        return None
    if found.whole_line:
        line_start = run_text.rstrip().rfind("\n") + 1
        if line_start == 0 and len(run) != len(paragraph.segments):
            return None
    return (run, run_text, found)


def _cut_run_text(
    body: tuple[NativeParagraph, ...], run: list[NativeTextSegment], run_text: str, start: int
) -> tuple[NativeParagraph, ...]:
    """The body with the run's text from ``start`` removed, keeping each segment's marks.

    The same cut serves the whole-line removal and the D13 whole-text word
    keep; only the start differs. A paragraph left with no segments is dropped.
    """
    paragraph = body[-1]
    kept_text = run_text[:start].rstrip()
    kept: list[NativeTextSegment] = []
    remaining = len(kept_text)
    for segment in run:
        if remaining <= 0:
            break
        if len(segment.text) <= remaining:
            kept.append(segment)
            remaining -= len(segment.text)
        else:
            kept.append(segment.model_copy(update={"text": segment.text[:remaining]}))
            remaining = 0
    head = paragraph.segments[: len(paragraph.segments) - len(run)]
    settled_paragraph = paragraph.model_copy(update={"segments": (*head, *kept)})
    return (*body[:-1], settled_paragraph) if settled_paragraph.segments else body[:-1]


def _body_keeps_text(body: tuple[NativeParagraph, ...]) -> bool:
    """Whether any paragraph keeps text, a gap or a picture."""
    for paragraph in body:
        for placed in paragraph.segments:
            if isinstance(placed, NativeTextSegment):
                if placed.text.strip():
                    return True
            elif isinstance(placed, (NativeGapSegment, NativeAssetSegment)):
                return True
    return False


def _one_word_head_label_start(run_text: str) -> int | None:
    """The label start when a whole points-only line is the whole question text (D13).

    A last line of one letter-only word and a points label ("Max 36p",
    "Show (2 p)") leaves whole only when the question keeps other text; when
    that line is the whole question text, the word stays and only the label
    leaves, with the blank space before it. A bare label ("(2 p)"), a head
    with a colon ("Poäng:") and longer heads never count: the line stays.
    """
    stripped = run_text.rstrip()
    line_start = stripped.rfind("\n") + 1
    line = stripped[line_start:]
    matches = list(POINT_LABEL.finditer(line))
    if len(matches) != 1:
        return None
    match = matches[0]
    if re.fullmatch(r"[^\W\d_]+", line[: match.start()].strip()) is None:
        return None
    start = line_start + match.start()
    while start > line_start and stripped[start - 1] in " \t":
        start -= 1
    return start


def body_without_trailing_points(
    body: tuple[NativeParagraph, ...], points: int | float | None
) -> tuple[NativeParagraph, ...]:
    """The body without trailing points wording that equals the given points.

    Only the last paragraph is examined, through its trailing run of text
    segments; a paragraph ending in a gap or a picture is never touched. A
    heading last paragraph is never touched here either: the heading rule
    owns it, so a terminal topic word is kept (D12 Correction, R2). A whole
    points line leaves only when its line starts inside the run. Each
    segment keeps its marks; a paragraph left with no segments is dropped. A
    body left with no text, gap or picture keeps its original paragraphs,
    except for a whole-text line of one letter-only word and a label (D13):
    the word stays and only the label leaves.
    """
    if points is None:
        return body
    if body and body[-1].heading_level is not None:
        return body
    located = _trailing_run_wording(body)
    if located is None:
        return body
    run, run_text, found = located
    if found.value != points:
        return body
    settled = _cut_run_text(body, run, run_text, found.start)
    if _body_keeps_text(settled):
        return settled
    if found.whole_line:
        label_start = _one_word_head_label_start(run_text)
        if label_start is not None:
            narrowed = _cut_run_text(body, run, run_text, label_start)
            if _body_keeps_text(narrowed):
                return narrowed
    return body


def _points_only_word_head_label_start(run_text: str) -> int | None:
    """The label start when a points-only last line keeps a one-word head.

    D12 fourth extension: an empty head or one ending in a colon leaves whole,
    so only a one-letter-word head without a colon ("Tempus", "Max") trims to
    the word; a longer head never reaches here, since a points-only line holds
    at most a two-word head ending in a colon.
    """
    stripped = run_text.rstrip()
    line_start = stripped.rfind("\n") + 1
    line = stripped[line_start:]
    if not points_only_line(line):
        return None
    matches = list(POINT_LABEL.finditer(line))
    if len(matches) != 1:
        return None
    match = matches[0]
    head = line[: match.start()]
    if not head.strip() or head.rstrip().endswith(":"):
        return None
    if re.fullmatch(r"[^\W\d_]+", head.strip()) is None:
        return None
    start = line_start + match.start()
    while start > line_start and stripped[start - 1] in " \t":
        start -= 1
    return start


def _first_paragraph_bare_only_value(run_text: str) -> int | float | None:
    """The value when a first paragraph holds only points wording.

    D12 extension E: ``heading_level`` comes from the Word heading style, so a
    heading chunk without a style level reaches the final gate as a plain first
    paragraph holding only its points wording. A points-only line with an empty
    or colon head ("Poäng: 2 poäng", "Max poäng: 6 p") or a bare label as the
    paragraph's only words ("1 point") counts; a one-word head without a colon
    ("Tempus 3 poäng", "Max 36p") keeps its word through the label trim, a
    paragraph with other words ("Uppgift 3 – 4 poäng",
    "Beskriv fotosyntesen, 2 p") and a parenthesised label (the
    parenthesised rule's case) never count.
    """
    stripped = run_text.strip()
    matches = list(POINT_LABEL.finditer(stripped))
    if len(matches) != 1:
        return None
    match = matches[0]
    if match.group().startswith("("):
        return None
    if points_only_line(stripped):
        if _points_only_word_head_label_start(stripped) is not None:
            return None
        return label_points(match.group())
    if stripped[: match.start()].strip():
        return None
    if stripped[match.end() :].strip(" \t.,;:!?"):
        return None
    return label_points(match.group())


def _without_bare_only_first_paragraph(
    body: tuple[NativeParagraph, ...], points: int | float
) -> tuple[NativeParagraph, ...]:
    """The body without a first paragraph that holds only points wording.

    The paragraph is dropped whole when its wording's number equals the points
    and the body keeps other text, gap or picture; a one-word head without a
    colon keeps its word through the label trim instead, and a differing
    number leaves the body untouched while nothing is recorded.
    """
    paragraph = body[0]
    texts: list[str] = []
    for segment in paragraph.segments:
        if not isinstance(segment, NativeTextSegment):
            return body
        texts.append(segment.text)
    if _first_paragraph_bare_only_value("".join(texts)) != points:
        return body
    if _body_keeps_text(body[1:]):
        return body[1:]
    return body


def body_without_first_paragraph_points(
    body: tuple[NativeParagraph, ...], points: int | float | None
) -> tuple[NativeParagraph, ...]:
    """The body without points wording ending its first paragraph.

    A parenthesised label ending the first paragraph's last line leaves with
    the blank space before it when its number equals the given points, heading
    or not; the paragraph keeps its heading level. A last line that is a
    points-only line is cut by its head shape instead, for bare and
    parenthesised labels alike: an empty or colon head leaves the whole line,
    a one-word head without a colon keeps its word and loses only the label
    (D12 Correction); a first paragraph that holds only points wording with
    an empty or colon head (a points-only line such as "Poäng: 2 poäng", or
    one bare label as its only words, "1 point") is dropped whole when its
    number equals the points and the body keeps other text (D12 E); a label
    beside other words stays. A one-paragraph body is the
    end-of-body rule's case, and a differing number records nothing. The cut
    keeps each segment's marks; a paragraph left with no segments is dropped
    when the body keeps other text, while a body of only that label stays (D6).
    """
    if points is None or len(body) < 2:
        return body
    located = _trailing_run_wording(body[:1])
    if located is None:
        return _without_bare_only_first_paragraph(body, points)
    run, run_text, found = located
    if found.value != points:
        return body
    if found.whole_line:
        start = _points_only_line_start(run_text)
    else:
        start = found.start
    paragraph = body[0]
    kept_text = run_text[:start].rstrip()
    kept: list[NativeTextSegment] = []
    remaining = len(kept_text)
    for segment in run:
        if remaining <= 0:
            break
        if len(segment.text) <= remaining:
            kept.append(segment)
            remaining -= len(segment.text)
        else:
            kept.append(segment.model_copy(update={"text": segment.text[:remaining]}))
            remaining = 0
    head = paragraph.segments[: len(paragraph.segments) - len(run)]
    settled_paragraph = paragraph.model_copy(update={"segments": (*head, *kept)})
    settled = (settled_paragraph, *body[1:]) if settled_paragraph.segments else body[1:]
    for kept_paragraph in settled:
        for placed in kept_paragraph.segments:
            if isinstance(placed, NativeTextSegment):
                if placed.text.strip():
                    return settled
            elif isinstance(placed, (NativeGapSegment, NativeAssetSegment)):
                return settled
    return body


# One trailing dash or colon with the blank space before it, left by a
# bare-label cut at the end of a heading paragraph ("Uppgift 3 –" gives
# "Uppgift 3"; an attached colon is stripped the same way, "Fråga 2:").
_HEADING_TRAILING_SEPARATOR = re.compile(r"[ \t]*[–—\-:]$")
# A dash or colon with the blank space after it, before a bare label at the
# end of a heading line ("Uppgift 3 – 4 poäng", "Fråga 2: 1 point").
_HEADING_BARE_LABEL_SEPARATOR = re.compile(r"[–—\-:][ \t]+$")


def _whole_line_start(run_text: str) -> int:
    """The cut start that drops the run's whole last line with its newline."""
    stripped = run_text.rstrip()
    line_start = stripped.rfind("\n") + 1
    return line_start - 1 if line_start else 0


def _points_only_line_start(run_text: str) -> int:
    """The cut start for a last line that is a points-only line, by head shape.

    One head-shape decision for the heading and first-paragraph paths: a
    one-word head without a colon keeps its word and loses only the label,
    while an empty or colon head leaves the whole line.
    """
    label_start = _points_only_word_head_label_start(run_text)
    if label_start is not None:
        return label_start
    return _whole_line_start(run_text)


def _heading_bare_label_cut(
    paragraph: NativeParagraph,
) -> tuple[list[NativeTextSegment], str, int, int | float] | None:
    """The trailing run, cut start and value when a bare label ends the line after a separator.

    D12 Correction: a bare label in a heading leaves only when a dash or
    colon precedes it with a blank space before the label ("Uppgift 3 –
    4 poäng" gives "Uppgift 3", "Fråga 2: 1 point" gives "Fråga 2"). A bare
    label ending a sentence or a range ("Använd mellan 3 poäng och
    5 poäng.", "Väljer eleven det får den 2 poäng.") stays. A parenthesised
    label is the shared wording's case, several labels never count, and a
    label with more words after it never matches.
    """
    located = _trailing_text_run(paragraph)
    if located is None:
        return None
    run, run_text = located
    stripped = run_text.rstrip()
    line_start = stripped.rfind("\n") + 1
    line = stripped[line_start:]
    matches = list(POINT_LABEL.finditer(line))
    if len(matches) != 1:
        return None
    match = matches[0]
    if match.group().startswith("("):
        return None
    if _HEADING_BARE_LABEL_SEPARATOR.search(line[: match.start()]) is None:
        return None
    value = label_points(match.group())
    if value is None:
        return None
    start = line_start + match.start()
    while start > line_start and stripped[start - 1] in " \t":
        start -= 1
    return (run, run_text, start, value)


def body_without_heading_points(
    body: tuple[NativeParagraph, ...], points: int | float | None
) -> tuple[NativeParagraph, ...]:
    """The body without points wording ending any heading paragraph.

    Any single points label ending a heading paragraph's last line leaves when
    its number equals the given points: a parenthesised label (only it
    leaves), a whole points-only line cut by its head shape (an empty or
    colon head leaves whole, a one-word head without a colon keeps its word,
    D12 Correction), or a bare label a dash or colon precedes with a blank
    space before it (it leaves with the blank space, plus the separator).
    Any other bare label in a heading stays, so a sentence or range ending
    never loses words. The paragraph keeps its heading level, and a
    non-heading paragraph is never touched. A differing number records nothing.
    The cut keeps each segment's marks; a paragraph left with no segments is
    dropped when the body keeps other text, while a body left with no text
    keeps its original paragraphs.
    """
    if points is None:
        return body
    settled = list(body)
    index = 0
    while index < len(settled):
        paragraph = settled[index]
        if paragraph.heading_level is None:
            index += 1
            continue
        located = _trailing_run_wording((paragraph,))
        bare_trim = False
        if located is None:
            bare = _heading_bare_label_cut(paragraph)
            if bare is None:
                index += 1
                continue
            run, run_text, start, value = bare
            if value != points:
                index += 1
                continue
            bare_trim = True
        else:
            run, run_text, found = located
            if found.value != points:
                index += 1
                continue
            if found.whole_line:
                start = _points_only_line_start(run_text)
            else:
                start = found.start
        kept_text = run_text[:start].rstrip()
        if bare_trim:
            kept_text = _HEADING_TRAILING_SEPARATOR.sub("", kept_text)
        kept: list[NativeTextSegment] = []
        remaining = len(kept_text)
        for segment in run:
            if remaining <= 0:
                break
            if len(segment.text) <= remaining:
                kept.append(segment)
                remaining -= len(segment.text)
            else:
                kept.append(segment.model_copy(update={"text": segment.text[:remaining]}))
                remaining = 0
        head = paragraph.segments[: len(paragraph.segments) - len(run)]
        settled_paragraph = paragraph.model_copy(update={"segments": (*head, *kept)})
        if settled_paragraph.segments:
            settled[index] = settled_paragraph
            index += 1
        elif _body_keeps_text(tuple((*settled[:index], *settled[index + 1 :]))):
            del settled[index]
        else:
            index += 1
    return tuple(settled)


def _heading_last_leftover(body: tuple[NativeParagraph, ...], points: int | float) -> str | None:
    """The wording a terminal heading would leave at an equal number, when it differs.

    One shape decision serves the cut and the recording: the shared run
    wording decides parenthesised and whole-line shapes, the latter cut by
    the head shape, while the bare-label cut decides separator-preceded bare
    labels; any other bare ending stays and records nothing.
    """
    paragraph = body[-1]
    located = _trailing_run_wording((paragraph,))
    if located is not None:
        run, run_text, found = located
        if found.value == points:
            return None
        start = _points_only_line_start(run_text) if found.whole_line else found.start
        if run_text[:start].rstrip().strip() or _body_keeps_text(body[:-1]):
            return run_text[start:].strip()
        return None
    bare = _heading_bare_label_cut(paragraph)
    if bare is None:
        return None
    run, run_text, start, value = bare
    if value == points:
        return None
    kept_text = _HEADING_TRAILING_SEPARATOR.sub("", run_text[:start].rstrip())
    if kept_text.strip() or _body_keeps_text(body[:-1]):
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
    located = _trailing_run_wording(body)
    if located is None:
        return None
    run, run_text, found = located
    if found.value == points:
        return None
    paragraph = body[-1]
    kept_text = run_text[: found.start].rstrip()
    kept: list[NativeTextSegment] = []
    remaining = len(kept_text)
    for segment in run:
        if remaining <= 0:
            break
        if len(segment.text) <= remaining:
            kept.append(segment)
            remaining -= len(segment.text)
        else:
            kept.append(segment.model_copy(update={"text": segment.text[:remaining]}))
            remaining = 0
    head = paragraph.segments[: len(paragraph.segments) - len(run)]
    settled_paragraph = paragraph.model_copy(update={"segments": (*head, *kept)})
    settled = (*body[:-1], settled_paragraph) if settled_paragraph.segments else body[:-1]
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
