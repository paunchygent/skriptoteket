"""Project document instructions while retaining deterministic source typography."""

from collections.abc import Mapping

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import ProducedMetadata
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_instruction_runs import _shown_heading
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import NativeParagraph
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import (
    body_asset_ids,
    body_plain_text,
    source_paragraphs,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_format_coverage import (
    complete_source_formatting,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_formatting import (
    SourceFormatting,
    formatted_text,
)


def instruction_paragraphs(
    instruction: ProducedMetadata, by_anchor: Mapping[str, DocxChunk]
) -> tuple[NativeParagraph, ...]:
    """Keep admitted wording when source marks and picture locations are accounted for."""
    sources = tuple(by_anchor[a] for a in instruction.source_anchors if a in by_anchor)
    raw = source_paragraphs(sources)
    if body_plain_text(raw) == instruction.text:
        return raw
    normalized = source_paragraphs(
        _shown_heading(chunk, None) if chunk.kind == "heading" else chunk for chunk in sources
    )
    if body_plain_text(normalized) == instruction.text:
        return raw if any(chunk.images or chunk.missing_images for chunk in sources) else normalized
    if body_asset_ids(raw):
        raise ValueError(
            f"instruction pictures have no faithful place: {instruction.source_anchors}"
        )
    source = SourceFormatting(sources)
    body = formatted_text(instruction.text, source)
    return complete_source_formatting(
        sources, (source,), source, body, printed_label=None, answers={}, can_rebuild_body=True
    )
