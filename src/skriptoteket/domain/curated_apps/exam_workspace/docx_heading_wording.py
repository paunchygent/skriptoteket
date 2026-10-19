"""A printed heading's shown wording: without its question number.

An item heading keeps its points wording for the final gate; only an
instruction heading loses its points label here. Deleting the label is
deterministic and keeps each shown character's source index, so a picture in
the heading stays at its place in the shown wording.
"""

import re
from dataclasses import replace

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import (
    POINT_LABEL,
    QUESTION_HEADING_LABEL,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.source_format_projection import projected_chunk


def heading_wording(chunk: DocxChunk, item: NativeExamItem | None) -> str:
    """A printed heading's wording without its question number.

    An item heading keeps its points wording; the final gate owns its removal
    (D12, review F1). Only a heading with no item loses its points label here.
    What remains is the heading as printed; a heading that is only a question
    number and points leaves nothing. A numbered question line set in a heading
    style, such as "Fråga 6. Ange …", leaves its stem, which the item already prints.
    """
    return _heading_content(chunk, item, QUESTION_HEADING_LABEL.match(chunk.text))[0]


def _heading_content(
    chunk: DocxChunk, item: NativeExamItem | None, question_label: re.Match[str] | None
) -> tuple[str, tuple[int, ...]]:
    """Normalize heading wording while retaining each shown character's source index.

    An item heading keeps its points wording; the final gate owns its removal.
    Only a heading with no item loses its points label here. Deleted labels
    consume no shown characters. A picture in deleted wording therefore stays at
    that boundary; surviving words and collapsed whitespace keep their order.
    """
    characters = list(chunk.text)
    origins = list(range(len(chunk.text)))
    if item is None:
        for match in reversed(list(POINT_LABEL.finditer(chunk.text))):
            characters[match.start() : match.end()] = [" "]
            origins[match.start() : match.end()] = [match.start()]
    # An item heading keeps its points wording; the final gate owns it (D12, review F1).
    stripped = "".join(characters)
    words = list(re.finditer(r"\S+", stripped))
    normalized: list[int] = []
    for word in words:
        if normalized:
            normalized.append(origins[word.start() - 1])
        normalized.extend(origins[word.start() : word.end()])
    text = " ".join(word.group() for word in words)
    label = (item.printed_label or "") if item is not None else ""
    if question_label is not None:
        # The same source parse supplies the eventual item's label. Source indices
        # survive points deletion and whitespace normalization above.
        prefix = sum(origin < question_label.end() for origin in normalized)
    elif label and text.casefold().startswith(label.casefold()):
        # A producer may label a non-numbered question, for example a lettered subpart.
        prefix = len(label)
        prefix += len(text[prefix:]) - len(text[prefix:].lstrip(" .):-"))
    else:
        prefix = 0
    text = text[prefix:]
    normalized = normalized[prefix:]
    left = len(text) - len(text.lstrip())
    text = text.strip().rstrip(" ,;")
    return text, tuple(normalized[left : left + len(text)])


def shown_heading(
    chunk: DocxChunk, item: NativeExamItem | None, question_label: re.Match[str] | None
) -> DocxChunk:
    """Place every picture through the same deterministic heading wording as heading text.

    An item heading keeps its points wording; the final gate owns its removal
    (D12, review F1). Only a heading with no item loses its points label here.
    """
    text, origins = _heading_content(chunk, item, question_label)
    if text == chunk.text:
        return chunk

    def shown_offset(offset: int) -> int:
        return sum(origin < offset for origin in origins)

    return replace(
        projected_chunk(chunk, text, origins),
        images=tuple(
            replace(
                image, offset=shown_offset(image.offset), marked_offset=shown_offset(image.offset)
            )
            for image in chunk.images
        ),
        missing_images=tuple(
            replace(
                image, offset=shown_offset(image.offset), marked_offset=shown_offset(image.offset)
            )
            for image in chunk.missing_images
        ),
    )
