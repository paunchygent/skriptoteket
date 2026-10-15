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
from skriptoteket.domain.curated_apps.exam_workspace.source_format_coverage import entry_label_end
from skriptoteket.domain.curated_apps.exam_workspace.source_format_scope import visible_intervals
from skriptoteket.domain.curated_apps.exam_workspace.source_formatted_entries import (
    apply_entry_ownership,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_formatting import SourceFormatting
from skriptoteket.domain.curated_apps.exam_workspace.source_native_carriers import (
    emitted_positions,
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
    text = "\n".join(chunk.text for chunk in chunks)
    carrier_spans: tuple[tuple[int, int], ...] = ()
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
    wordings = {surface.sequence: surface.texts for surface in surfaces}
    emitted = frozenset().union(
        *(
            emitted_positions(
                text[owner.start : owner.end],
                wordings[owner.sequence][owner.ordinal - 1],
                owner.start,
            )
            for owner in ownership.owners
            if owner.start >= 0
        )
    )
    body_wording = "\n".join(
        "".join(
            segment.text
            for segment in paragraph.segments
            if segment.kind == "text" and segment.text
        )
        for paragraph in produced.body
    )
    body_regions = tuple(visible_intervals(0, len(text), ownership.exclusion_ranges()))
    emitted |= frozenset().union(
        *(emitted_positions(text[start:end], body_wording, start) for start, end in body_regions)
    )
    regions = tuple(
        (
            owner.start
            + (
                entry_label_end(text[owner.start : owner.end], owner.ordinal) or 0
                if owner.label_start is not None
                else 0
            ),
            owner.end,
        )
        for owner in ownership.owners
        if owner.start >= 0
    )
    carrier_spans = native_carrier_spans(
        text,
        points=produced.points,
        emitted=emitted,
        regions=regions,
        body_regions=body_regions,
    )
    surfaces = tuple(
        EntrySurface(
            surface.sequence, surface.texts, SourceFormatting(chunks, excluded=carrier_spans)
        )
        for surface in surfaces
    )
    for surface in surfaces:
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
