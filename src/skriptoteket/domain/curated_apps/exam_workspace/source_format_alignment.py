"""Character-level typography projection when the model rewrites source wording.

SequenceMatcher is an alignment tool, not an authority to choose formatting.
Only equal character blocks inherit source marks. Insertions remain unmarked.
A source marked character must be represented by text or by a gap's source
answer before the projection is admitted. Whitespace carries no loss signal.
"""

import re
from difflib import SequenceMatcher

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeParagraph,
    NativeSegment,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_format_gap_alignment import gap_spans

# Existing inline-key recognition shared by projection and source ownership.
ANSWER_LABEL = re.compile(r"\b(?:svar|facit|answer key|correct answers?)\s*:", re.IGNORECASE)


def answer_label_cut(text: str, start: int, end: int) -> int | None:
    """Cut the span at the first inline answer label, with any wrapper ``(``.

    Returns the label's start, or the wrapper "(" before it when only whitespace
    lies between them. Returns None when no answer label stands in the span.
    """
    label = ANSWER_LABEL.search(text, start, end)
    if label is None:
        return None
    opening = text.rfind("(", start, label.start())
    if opening >= start and not text[opening + 1 : label.start()].strip():
        return opening
    return label.start()


def align_paragraph(
    paragraph: NativeParagraph,
    source_text: str,
    source_marks: list[tuple[str, ...]],
    heading: int | None,
    answers: dict[str, tuple[str, ...]],
    ignored: tuple[str, ...],
) -> tuple[NativeParagraph, bool, set[int]]:
    """Return projected text and whether a student-visible source mark was lost."""
    parts: list[str] = []
    # A gap contributes its copied answer to alignment only, never visible text.
    for segment in paragraph.segments:
        if segment.kind == "text":
            parts.append(segment.text)
        elif segment.kind == "gap":
            values = answers.get(segment.gap_id, ())
            answer = next((value for value in values if value and value in source_text), "\ufffc")
            parts.append(answer)
        else:
            parts.append("\ufffc")
    target = "".join(parts)
    mapped: dict[int, int] = {}
    represented: set[int] = set()
    alignment_source = source_text
    inline_key = ANSWER_LABEL.search(source_text)
    if inline_key and not ANSWER_LABEL.search(target):
        # The returned prompt may deliberately use the worked expression after
        # an inline key label. Do not let an identical unmarked word in the
        # original question steal the match from that formatted expression.
        prefix = "".join(
            char if source_marks[index] else "\uffff"
            for index, char in enumerate(source_text[: inline_key.end()])
        )
        alignment_source = prefix + source_text[inline_key.end() :]
    for block in SequenceMatcher(
        None, alignment_source, target, autojunk=False
    ).get_matching_blocks():
        for offset in range(block.size):
            mapped[block.b + offset] = block.a + offset
            represented.add(block.a + offset)
    gaps = [segment for segment in paragraph.segments if segment.kind == "gap"]
    placements = gap_spans(source_text, gaps, answers)
    if placements is not None:
        for start, end in placements:
            represented.update(range(start, end))
    # The caller supplies the exact located structural span, including its
    # delimiter. Following punctuation belongs to content, not to the label.
    for label in ignored:
        if label and source_text.startswith(label):
            represented.update(range(len(label)))
    lost = any(
        marks and not source_text[index].isspace() and index not in represented
        for index, marks in enumerate(source_marks)
    )
    segments: list[NativeSegment] = []
    cursor = 0
    for segment, shown in zip(paragraph.segments, parts, strict=True):
        if segment.kind != "text":
            segments.append(segment)
        else:
            start = 0
            while start < len(shown):
                origin = mapped.get(cursor + start)
                marks = source_marks[origin] if origin is not None else ()
                end = start + 1
                while end < len(shown):
                    origin = mapped.get(cursor + end)
                    if (source_marks[origin] if origin is not None else ()) != marks:
                        break
                    end += 1
                segments.append(NativeTextSegment(text=shown[start:end], marks=marks))
                start = end
        cursor += len(shown)
    return NativeParagraph(heading_level=heading, segments=tuple(segments)), lost, represented
