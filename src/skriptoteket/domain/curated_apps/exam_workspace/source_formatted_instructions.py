"""Project document instructions while retaining deterministic source typography."""

from collections.abc import Mapping

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import ProducedMetadata
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_heading_wording import shown_heading
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import QUESTION_HEADING_LABEL
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import NativeParagraph
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import (
    body_asset_ids,
    body_plain_text,
    source_paragraphs,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_format_coverage import (
    complete_source_formatting,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_format_errors import (
    FormattingTransferError,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_formatting import (
    SourceFormatting,
    formatted_text,
)


def instruction_paragraphs(
    instruction: ProducedMetadata, by_anchor: Mapping[str, DocxChunk]
) -> tuple[NativeParagraph, ...]:
    """Keep admitted wording when source marks and picture locations are accounted for."""
    # ``by_anchor`` carries the document's chunk order; the model's anchor list is a
    # selection, not an ordering, so every source body stays in source order.
    identified = frozenset(instruction.source_anchors)
    sources = tuple(chunk for anchor, chunk in by_anchor.items() if anchor in identified)
    raw = source_paragraphs(sources)
    if body_plain_text(raw) == instruction.text:
        return raw
    normalized = source_paragraphs(
        shown_heading(chunk, None, QUESTION_HEADING_LABEL.match(chunk.text))
        if chunk.kind == "heading"
        else chunk
        for chunk in sources
    )
    if body_plain_text(normalized) == instruction.text:
        return raw if any(chunk.images or chunk.missing_images for chunk in sources) else normalized
    if body_asset_ids(raw):
        raise ValueError(
            f"instruction pictures have no faithful place: {instruction.source_anchors}"
        )
    source = SourceFormatting(sources, foreign=())
    try:
        body = formatted_text(instruction.text, source)
        return complete_source_formatting(
            sources, (source,), source, body, printed_label=None, answers={}, can_rebuild_body=True
        )
    except FormattingTransferError:
        # An instruction naming several source paragraphs can be rewritten so that no
        # single paragraph matches it, and the generic item-body reconstruction can
        # refuse instruction wording that is legitimate here (a literal "answer key:"
        # line, for example). The complete identified source body is the contracted
        # reconstruction: every mark and paragraph level as read. Pictures have
        # already failed closed above, so this body is text only.
        return raw
