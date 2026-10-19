"""Cut review bodies at the inline answer key (TASK-SKRIPT-39-04-17).

When a gap count mismatch sends an item to review, each body paragraph is cut
from its inline answer label onward, so the source word stays and the key stays
out. A picture or a gap after the cut stays, after the kept text. A paragraph
the cut leaves empty is removed together with its aligned chunk entry.
"""

from skriptoteket.domain.curated_apps.exam_workspace.docx_item_alignment import (
    AlignedItem,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeParagraph,
    NativeSegment,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_format_alignment import (
    answer_label_cut,
)


def _cut_paragraph(paragraph: NativeParagraph) -> NativeParagraph | None:
    """The paragraph without its inline answer key, or None when the cut empties it."""
    joined = "".join(
        segment.text for segment in paragraph.segments if isinstance(segment, NativeTextSegment)
    )
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


def without_inline_answer_keys(aligned: AlignedItem) -> AlignedItem:
    """The item with every body paragraph cut from its inline answer label onward.

    A paragraph the cut leaves empty leaves together with its aligned chunk entry,
    so the body and its chunks stay the same length. The entries keep theirs.
    """
    shown: list[tuple[NativeParagraph, str | None]] = []
    for paragraph, chunk in zip(aligned.item.body, aligned.chunks, strict=True):
        cut = _cut_paragraph(paragraph)
        if cut is not None:
            shown.append((cut, chunk))
    return aligned.with_body(shown)
