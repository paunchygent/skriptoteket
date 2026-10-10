"""Map produced items to the native contract and assemble the build result."""

from uuid import UUID

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
    DocxBuildEvent,
    DocxBuildResult,
    ProducedItem,
    ProducedMetadata,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeAnswerKey,
    NativeAnswerKeyOrigin,
    NativeChoice,
    NativeExamDocument,
    NativeExamDocumentOrigin,
    NativeExamItem,
    NativeExamItemKind,
    NativeGap,
    NativeGapSegment,
    NativeItemReview,
    NativeItemReviewState,
    NativeParagraph,
    NativeParseOrigin,
    NativeSegment,
    NativeTextSegment,
)


def native_item(produced: ProducedItem) -> NativeExamItem:
    """Assign IDs and provenance; the native contract raises on any invalid shape."""
    choices = tuple(
        NativeChoice(choice_id=f"choice_{index:03d}", text=choice.text)
        for index, choice in enumerate(produced.choices, start=1)
    )
    correct = tuple(
        native.choice_id
        for native, choice in zip(choices, produced.choices, strict=True)
        if choice.correct
    )
    gaps: list[NativeGap] = []
    body: list[NativeParagraph] = []
    for paragraph in produced.body:
        segments: list[NativeSegment] = []
        for segment in paragraph.segments:
            if segment.kind == "gap":
                gap_id = f"gap_{len(gaps) + 1:03d}"
                gaps.append(
                    NativeGap(
                        gap_id=gap_id, accepted_values=segment.accepted_values, hint=segment.hint
                    )
                )
                segments.append(NativeGapSegment(gap_id=gap_id))
            else:
                segments.append(NativeTextSegment(text=segment.text or ""))
        body.append(NativeParagraph(segments=tuple(segments)))
    keyed = bool(correct) or any(gap.accepted_values for gap in gaps)
    if produced.kind is NativeExamItemKind.FREE_TEXT:
        origin = NativeAnswerKeyOrigin.NOT_APPLICABLE
    else:
        origin = NativeAnswerKeyOrigin.SOURCE_PROVIDED if keyed else NativeAnswerKeyOrigin.ABSENT
    return NativeExamItem(
        item_id="item_001",
        sequence=1,
        kind=produced.kind,
        title=produced.title,
        body=tuple(body),
        points=produced.points,
        choices=choices,
        gaps=tuple(gaps),
        answer_key=NativeAnswerKey(origin=origin, correct_choice_ids=correct),
        review=NativeItemReview(
            state=NativeItemReviewState.REVIEW_COMPLETE,
            parse_origin=NativeParseOrigin.LLM_PARSED,
        ),
        source_anchor=produced.source_anchors[0],
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


def _ordered_items(
    chunks: tuple[DocxChunk, ...],
    accepted: tuple[tuple[NativeExamItem, tuple[str, ...]], ...],
    review_reasons: dict[str, str],
) -> tuple[NativeExamItem, ...]:
    positions = {c.anchor: i for i, c in enumerate(chunks)}
    ordered = [(min(positions[a] for a in anchors), item) for item, anchors in accepted]
    ordered.extend(
        (positions[chunk.anchor], review_chunk_item(chunk, review_reasons[chunk.anchor]))
        for chunk in chunks
        if chunk.anchor in review_reasons
    )
    ordered.sort(key=lambda pair: pair[0])
    return tuple(
        item.model_copy(update={"item_id": f"item_{i:03d}", "sequence": i})
        for i, (_, item) in enumerate(ordered, start=1)
    )


def assemble_build_result(
    *,
    document_id: UUID,
    filename: str,
    source_sha256: str,
    chunks: tuple[DocxChunk, ...],
    accepted: tuple[tuple[NativeExamItem, tuple[str, ...]], ...] = (),
    review_reasons: dict[str, str],
    key_anchors: frozenset[str] = frozenset(),
    title: ProducedMetadata | None = None,
    instructions: tuple[ProducedMetadata, ...] = (),
    events: tuple[DocxBuildEvent, ...] = (),
    input_tokens: int | None = None,
    output_tokens: int | None = None,
) -> DocxBuildResult:
    """Keep facit chunks as teacher notes and every unbuilt chunk as a review item."""
    if not chunks:
        chunks = (DocxChunk("empty", "paragraph", "Dokumentet saknar läsbart innehåll."),)
        review_reasons = {"empty": "Dokumentet saknar läsbart innehåll."}
    notes = [chunk.text for chunk in chunks if chunk.anchor in key_anchors]
    notes.extend(dict.fromkeys(review_reasons[a] for a in review_reasons))
    document = NativeExamDocument(
        document_id=document_id,
        revision=1,
        title=title.text if title else filename,
        instructions=tuple(v.text for v in instructions),
        items=_ordered_items(chunks, accepted, review_reasons),
        origin=NativeExamDocumentOrigin(
            kind="docx_import",
            source_filename=filename,
            source_sha256=source_sha256,
            extractor_version="docx_ai_build_v2",
        ),
    )
    return DocxBuildResult(document, tuple(notes), input_tokens, output_tokens, events)
