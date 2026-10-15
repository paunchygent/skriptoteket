"""Prepare the question/entry ownership boundary before native body projection."""

from dataclasses import dataclass
from typing import TypeVar

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import ProducedItem
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_matching import (
    NativeMatchLeft,
    NativeMatchRight,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import NativeChoice
from skriptoteket.domain.curated_apps.exam_workspace.source_entry_ownership import (
    EntryOwnership,
    EntrySurface,
    plan_entry_ownership,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_formatted_entries import (
    apply_entry_ownership,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_formatting import SourceFormatting
from skriptoteket.domain.curated_apps.exam_workspace.source_native_carriers import (
    entry_answer_spans,
    native_carrier_spans,
)

Entry = TypeVar("Entry", NativeChoice, NativeMatchLeft, NativeMatchRight)


@dataclass(frozen=True)
class ItemSourceFormatting:
    body: SourceFormatting
    surfaces: tuple[EntrySurface, ...]
    ownership: EntryOwnership

    @property
    def sources(self) -> tuple[SourceFormatting, ...]:
        return (self.body, *(surface.source for surface in self.surfaces))

    def restore(self, sequence: str, entries: tuple[Entry, ...]) -> tuple[Entry, ...]:
        surface = next(surface for surface in self.surfaces if surface.sequence == sequence)
        return apply_entry_ownership(self.ownership, surface, entries, body_source=self.body)


def item_source_formatting(
    produced: ProducedItem, chunks: tuple[DocxChunk, ...]
) -> ItemSourceFormatting:
    carrier_spans = native_carrier_spans(
        "\n".join(chunk.text for chunk in chunks), produced.facit_text
    )
    surfaces = tuple(
        EntrySurface(sequence, texts, SourceFormatting(chunks, excluded=carrier_spans))
        for sequence, texts in (
            ("choices", tuple(choice.text for choice in produced.choices)),
            ("match_left", produced.match_left),
            ("match_right", produced.match_right),
        )
    )
    ownership = plan_entry_ownership(
        chunks,
        surfaces,
        body_texts=tuple(
            segment.text
            for paragraph in produced.body
            for segment in paragraph.segments
            if segment.kind == "text" and segment.text
        ),
    )
    carrier_spans = tuple(
        sorted(
            (
                *carrier_spans,
                *entry_answer_spans(surfaces[0].source.text, ownership, surfaces),
            )
        )
    )
    for surface in surfaces:
        surface.source.excluded = carrier_spans
        for start, end in carrier_spans:
            surface.source.covered.update(range(start, end))
    body = SourceFormatting(
        chunks,
        ignored=(produced.printed_label or "",),
        excluded=tuple(sorted((*ownership.exclusion_ranges(), *carrier_spans))),
    )
    for start, end in carrier_spans:
        body.covered.update(range(start, end))
    return ItemSourceFormatting(body, surfaces, ownership)
