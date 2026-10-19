"""Cut review bodies at the inline answer key, carrying the key into the facit.

TASK-SKRIPT-39-04-18.

When a gap count mismatch sends an item to review, each body paragraph is cut
from its inline answer label onward, so the source word stays and the key stays
out. A picture or a gap after the cut stays, after the kept text. A paragraph
the cut leaves empty is removed together with its aligned chunk entry.

Each cut paragraph gives one key line: the paragraph's leading list label when
it has one, then its source text from the cut point to the paragraph's text end,
verbatim, trailing whitespace trimmed. The lines join by newline in body order
into the item's ``facit_text``. A cut tail holding nothing after its label but
whitespace and blank runs (a printed answer line) is not a key and leaves
``facit_text`` as it was. ``answer_key.origin`` is untouched.
"""

from dataclasses import replace

from skriptoteket.domain.curated_apps.exam_workspace.docx_item_alignment import (
    AlignedItem,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import (
    BLANK_RUN,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeParagraph,
    NativeSegment,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_answer_space import (
    is_answer_line_text,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_format_alignment import (
    ANSWER_LABEL,
    answer_label_cut,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_format_coverage import (
    leading_entry_label_end,
)


def _joined_text(paragraph: NativeParagraph) -> str:
    return "".join(
        segment.text for segment in paragraph.segments if isinstance(segment, NativeTextSegment)
    )


def _cut_paragraph(paragraph: NativeParagraph) -> NativeParagraph | None:
    """The paragraph without its inline answer key, or None when the cut empties it."""
    joined = _joined_text(paragraph)
    cut = answer_label_cut(joined, 0, len(joined))
    if cut is None:
        return paragraph
    kept: list[NativeSegment] = []
    trailing: list[NativeSegment] = []
    offset = 0
    for segment in paragraph.segments:
        if isinstance(segment, NativeTextSegment):
            end = offset + len(segment.text)
            if end <= cut:
                kept.append(segment)
            elif offset < cut:
                kept.append(segment.model_copy(update={"text": segment.text[: cut - offset]}))
            offset = end
        elif offset < cut:
            kept.append(segment)
        else:
            trailing.append(segment)
    while kept and isinstance(kept[-1], NativeTextSegment):
        stripped = kept[-1].text.rstrip()
        if stripped:
            kept[-1] = kept[-1].model_copy(update={"text": stripped})
            break
        kept.pop()
    segments = (*kept, *trailing)
    if not segments:
        return None
    return paragraph.model_copy(update={"segments": segments})


def _key_line(paragraph: NativeParagraph) -> str | None:
    """The paragraph's carried key line, or None when its cut tail holds no key.

    The line is the paragraph's text-only wording from the cut point to its
    text end, verbatim with trailing whitespace trimmed; a gap or a picture
    after the cut is not text, so it is outside the line by construction. A
    tail holding nothing after its answer label but whitespace and blank runs
    is a printed answer line, never a key. A leading ordinal list label stays
    on the line, followed by one space.
    """
    joined = _joined_text(paragraph)
    cut = answer_label_cut(joined, 0, len(joined))
    if cut is None:
        return None
    tail = joined[cut:].rstrip()
    label = ANSWER_LABEL.search(joined, cut)
    if not tail or label is None:
        return None
    rest = joined[label.end() :].rstrip()
    if joined[cut] == "(" and rest.endswith(")"):
        rest = rest[:-1].rstrip()
    rest = BLANK_RUN.sub("", rest)
    if not rest.strip() or is_answer_line_text(rest):
        return None
    end = leading_entry_label_end(joined)
    if end is not None and end <= cut and joined[:end].rstrip():
        return f"{joined[:end].rstrip()} {tail}"
    return tail


def without_inline_answer_keys(aligned: AlignedItem) -> AlignedItem:
    """The item with every body paragraph cut from its inline answer label onward.

    A paragraph the cut leaves empty leaves together with its aligned chunk entry,
    so the body and its chunks stay the same length. The entries keep theirs.
    Each cut paragraph's key line joins the item's ``facit_text`` in body order;
    with no key line the item is untouched.
    """
    shown: list[tuple[NativeParagraph, str | None]] = []
    lines: list[str] = []
    for paragraph, chunk in zip(aligned.item.body, aligned.chunks, strict=True):
        cut = _cut_paragraph(paragraph)
        if cut is not None:
            shown.append((cut, chunk))
        line = _key_line(paragraph)
        if line is not None:
            lines.append(line)
    result = aligned.with_body(shown)
    if lines:
        result = replace(
            result, item=result.item.model_copy(update={"facit_text": "\n".join(lines)})
        )
    return result
