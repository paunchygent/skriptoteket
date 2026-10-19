"""Segment-preserving paragraph and body transformations.

When its number equals the item's points, ``body_without_trailing_points``
drops it from the last paragraph of a non-heading body (keeping the word of a
whole-text one-word line, D13), and ``body_without_first_paragraph_points``
drops a parenthesised label ending the first paragraph or a first paragraph
that is only points wording; ``body_without_heading_points`` drops an equal
label ending a heading paragraph anywhere in the body only as a parenthesised
label, as a bare label a dash or colon precedes, or as a whole points-only
line cut by the same head shape; any other bare label in a heading stays, so
a sentence or range ending never loses words. A heading last paragraph is
never the end-of-body rule's case.
"""

from __future__ import annotations

from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import (
    POINT_LABEL,
    label_points,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeAssetSegment,
    NativeGapSegment,
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.points_wording_shapes import (
    HEADING_BARE_LABEL_SEPARATOR,
    HEADING_TRAILING_SEPARATOR,
    TrailingPoints,
    first_paragraph_bare_only_value,
    one_word_head_label_start,
    points_only_line_start,
    trailing_points,
)


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


def trailing_run_wording(
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


def paragraph_keeping_run_text(
    paragraph: NativeParagraph, run: list[NativeTextSegment], kept_text: str
) -> NativeParagraph | None:
    """The paragraph with its trailing run cut to ``kept_text``'s length.

    Each kept segment keeps its marks; the last kept segment is truncated to
    the kept length. None when no segment is left; the caller decides what an
    emptied paragraph means for its body.
    """
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
    return settled_paragraph if settled_paragraph.segments else None


def _cut_run_text(
    body: tuple[NativeParagraph, ...], run: list[NativeTextSegment], run_text: str, start: int
) -> tuple[NativeParagraph, ...]:
    """The body with the run's text from ``start`` removed, keeping each segment's marks.

    The same cut serves the whole-line removal and the D13 whole-text word
    keep; only the start differs. A paragraph left with no segments is dropped.
    """
    paragraph = body[-1]
    kept_text = run_text[:start].rstrip()
    settled_paragraph = paragraph_keeping_run_text(paragraph, run, kept_text)
    return (*body[:-1], settled_paragraph) if settled_paragraph is not None else body[:-1]


def body_keeps_text(body: tuple[NativeParagraph, ...]) -> bool:
    """Whether any paragraph keeps text, a gap or a picture."""
    for paragraph in body:
        for placed in paragraph.segments:
            if isinstance(placed, NativeTextSegment):
                if placed.text.strip():
                    return True
            elif isinstance(placed, (NativeGapSegment, NativeAssetSegment)):
                return True
    return False


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
    located = trailing_run_wording(body)
    if located is None:
        return body
    run, run_text, found = located
    if found.value != points:
        return body
    settled = _cut_run_text(body, run, run_text, found.start)
    if body_keeps_text(settled):
        return settled
    if found.whole_line:
        label_start = one_word_head_label_start(run_text)
        if label_start is not None:
            narrowed = _cut_run_text(body, run, run_text, label_start)
            if body_keeps_text(narrowed):
                return narrowed
    return body


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
    if first_paragraph_bare_only_value("".join(texts)) != points:
        return body
    if body_keeps_text(body[1:]):
        return body[1:]
    return body


def body_without_first_paragraph_points(
    body: tuple[NativeParagraph, ...], points: int | float | None, allow_single_paragraph: bool
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
    beside other words stays. With ``allow_single_paragraph`` a one-paragraph
    body is this rule's case when the cut paragraph keeps text of its own,
    for a heading the reader read reaching the body alone; otherwise a
    one-paragraph body is the end-of-body rule's case, and a differing number
    records nothing. The cut keeps each segment's marks; a paragraph left
    with no segments is dropped when the body keeps other text, while a body
    of only that label stays (D6).
    """
    if points is None or (len(body) < 2 and not allow_single_paragraph):
        return body
    located = trailing_run_wording(body[:1])
    if located is None:
        return _without_bare_only_first_paragraph(body, points)
    run, run_text, found = located
    if found.value != points:
        return body
    if found.whole_line:
        start = points_only_line_start(run_text)
    else:
        start = found.start
    paragraph = body[0]
    kept_text = run_text[:start].rstrip()
    settled_paragraph = paragraph_keeping_run_text(paragraph, run, kept_text)
    settled = (settled_paragraph, *body[1:]) if settled_paragraph is not None else body[1:]
    for kept_paragraph in settled:
        for placed in kept_paragraph.segments:
            if isinstance(placed, NativeTextSegment):
                if placed.text.strip():
                    return settled
            elif isinstance(placed, (NativeGapSegment, NativeAssetSegment)):
                return settled
    return body


def heading_bare_label_cut(
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
    if HEADING_BARE_LABEL_SEPARATOR.search(line[: match.start()]) is None:
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
        located = trailing_run_wording((paragraph,))
        bare_trim = False
        if located is None:
            bare = heading_bare_label_cut(paragraph)
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
                start = points_only_line_start(run_text)
            else:
                start = found.start
        kept_text = run_text[:start].rstrip()
        if bare_trim:
            kept_text = HEADING_TRAILING_SEPARATOR.sub("", kept_text)
        settled_paragraph = paragraph_keeping_run_text(paragraph, run, kept_text)
        if settled_paragraph is not None:
            settled[index] = settled_paragraph
            index += 1
        elif body_keeps_text(tuple((*settled[:index], *settled[index + 1 :]))):
            del settled[index]
        else:
            index += 1
    return tuple(settled)
