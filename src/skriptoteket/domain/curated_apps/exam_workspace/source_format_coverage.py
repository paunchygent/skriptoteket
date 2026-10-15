"""Admit an item's typography only after accounting for every visible source mark."""

import re
from collections.abc import Iterable

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import POINT_LABEL
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import NativeParagraph
from skriptoteket.domain.curated_apps.exam_workspace.source_formatting import (
    FormattingTransferError,
    SourceFormatting,
)


def complete_source_formatting(
    chunks: tuple[DocxChunk, ...],
    sources: Iterable[SourceFormatting],
    body_source: SourceFormatting,
    body: tuple[NativeParagraph, ...],
    *,
    printed_label: str | None,
    answers: dict[str, tuple[str, ...]],
    can_rebuild_body: bool,
) -> tuple[NativeParagraph, ...]:
    covered = set().union(*(source.covered for source in sources))
    offset = 0
    for index, chunk in enumerate(chunks):
        if index:
            offset += 1
        # Assembly deterministically places source heading chunks; they are not
        # required to appear in the model's body before that placement happens.
        if chunk.kind == "heading":
            covered.update(range(offset, offset + len(chunk.text)))
        for match in POINT_LABEL.finditer(chunk.text):
            covered.update(range(offset + match.start(), offset + match.end()))
        if printed_label and chunk.text.startswith(printed_label):
            covered.update(range(offset, offset + len(printed_label)))
            at = len(printed_label)
            while at < len(chunk.text) and (chunk.text[at].isspace() or chunk.text[at] in ".):-"):
                covered.add(offset + at)
                at += 1
        # Choice/matching source labels have native identifiers, not rich text.
        label = re.match(r"^\s*[A-Za-z0-9]+[.)]\s+", chunk.text)
        if label:
            covered.update(range(offset, offset + label.end()))
        offset += len(chunk.text)
    missing = [
        index
        for index, marks in enumerate(body_source.marks)
        if marks and not body_source.text[index].isspace() and index not in covered
    ]
    if not missing:
        return body
    if not can_rebuild_body:
        raise FormattingTransferError("unrepresented source marks cannot be isolated from entries")
    return body_source.rebuild_body(answers)
