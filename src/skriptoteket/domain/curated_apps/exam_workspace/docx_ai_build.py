"""DOCX result assembly and the stable batched-build public interface."""

from uuid import UUID

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_admission import (
    validate_build_entry as validate_build_entry,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
    DocxBuildEntry as DocxBuildEntry,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
    DocxBuildEnvelope as DocxBuildEnvelope,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
    DocxBuildResult as DocxBuildResult,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
    KeyEvidence as KeyEvidence,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
    SourceEvidence as SourceEvidence,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
    SourceText as SourceText,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_schema import (
    docx_build_output_spec as docx_build_output_spec,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_schema import (
    parse_build_entry as parse_build_entry,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_source import (
    answer_key_chunks as answer_key_chunks,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_source import (
    normalize_text as normalize_text,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_source import (
    validate_source_text as validate_source_text,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeAnswerKey,
    NativeAnswerKeyOrigin,
    NativeExamDocument,
    NativeExamDocumentOrigin,
    NativeExamItem,
    NativeExamItemKind,
    NativeItemReview,
    NativeItemReviewState,
    NativeParagraph,
    NativeParseOrigin,
    NativeTextSegment,
)


def _accounted_chunks(
    chunks: tuple[DocxChunk, ...],
    accepted: tuple[tuple[NativeExamItem, tuple[str, ...]], ...],
    title: SourceText | None,
    instructions: tuple[SourceText, ...],
) -> tuple[set[str], list[str]]:
    claimed = {a for _, anchors in accepted for a in anchors}
    notes: list[str] = []
    # Only fully accounted metadata chunks are consumed; partial ones remain reviewable.
    for chunk in chunks:
        metadata = [
            v.text
            for v in (*instructions, *((title,) if title else ()))
            if chunk.anchor in v.source_anchors
        ]
        if metadata and normalize_text(" ".join(metadata)) == normalize_text(chunk.text):
            claimed.add(chunk.anchor)
    if accepted:
        for chunk in answer_key_chunks(chunks):
            claimed.add(chunk.anchor)
            notes.append(chunk.text)
    return claimed, notes


def _ordered_items(
    chunks: tuple[DocxChunk, ...],
    accepted: tuple[tuple[NativeExamItem, tuple[str, ...]], ...],
    claimed: set[str],
    reason: str,
) -> tuple[NativeExamItem, ...]:
    positions = {c.anchor: i for i, c in enumerate(chunks)}
    ordered = [(min(positions[a] for a in anchors), item) for item, anchors in accepted]
    for chunk in chunks:
        if chunk.anchor not in claimed:
            ordered.append((positions[chunk.anchor], review_chunk_item(chunk, reason)))
    if not ordered:
        ordered.append(
            (
                0,
                review_chunk_item(
                    DocxChunk("empty", "paragraph", "Dokumentet saknar läsbart innehåll."), reason
                ),
            )
        )
    ordered.sort(key=lambda pair: pair[0])
    return tuple(
        item.model_copy(update={"item_id": f"item_{i:03d}", "sequence": i})
        for i, (_, item) in enumerate(ordered, start=1)
    )


def review_chunk_item(chunk: DocxChunk, reason: str) -> NativeExamItem:
    return NativeExamItem(
        item_id="item_001",
        sequence=1,
        kind=NativeExamItemKind.FREE_TEXT,
        body=(
            NativeParagraph(segments=(NativeTextSegment(text=chunk.text or "Tomt källstycke."),)),
        ),
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
        review=NativeItemReview(
            state=NativeItemReviewState.REVIEW_REQUIRED,
            parse_origin=NativeParseOrigin.DETERMINISTIC,
            reasons=(reason,),
        ),
        source_anchor=chunk.anchor,
    )


def assemble_build_result(
    *,
    document_id: UUID,
    filename: str,
    source_sha256: str,
    chunks: tuple[DocxChunk, ...],
    accepted: tuple[tuple[NativeExamItem, tuple[str, ...]], ...] = (),
    title: SourceText | None = None,
    instructions: tuple[SourceText, ...] = (),
    reason: str,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
) -> DocxBuildResult:
    claimed, notes = _accounted_chunks(chunks, accepted, title, instructions)
    items = _ordered_items(chunks, accepted, claimed, reason)
    if any(item.review.state is NativeItemReviewState.REVIEW_REQUIRED for item in items):
        notes.append(reason)
    document = NativeExamDocument(
        document_id=document_id,
        revision=1,
        title=title.text if title else filename,
        instructions=tuple(v.text for v in instructions),
        items=items,
        origin=NativeExamDocumentOrigin(
            kind="docx_import",
            source_filename=filename,
            source_sha256=source_sha256,
            extractor_version="docx_ai_build_v1",
        ),
    )
    return DocxBuildResult(document, tuple(notes), input_tokens, output_tokens)
