"""Map produced items to the native contract and assemble the build result."""

from collections.abc import Mapping
from types import MappingProxyType
from uuid import UUID

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
    DocxBuildEvent,
    DocxBuildResult,
    ProducedItem,
    ProducedMetadata,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_section_instructions import (
    SectionInstructions,
    place_section_instructions,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import (
    title_without_answer_key,
)
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
    NativeMatchLeft,
    NativeMatchPair,
    NativeMatchRight,
    NativeParagraph,
    NativeParseOrigin,
    NativeSegment,
    NativeTextSegment,
)

_BLANK = NativeTextSegment(text="____")


# No shared context governs two or more questions: every instruction is placed by its run.
NOTHING_GOVERNED: Mapping[str, frozenset[str]] = MappingProxyType({})


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
            if segment.kind == "gap" and produced.kind is not NativeExamItemKind.GAP_FILL:
                # Only gap_fill answers in a gap; another kind shows a printed blank as text.
                segments.append(_BLANK)
            elif segment.kind == "gap":
                gap_id = f"gap_{len(gaps) + 1:03d}"
                gaps.append(NativeGap(gap_id=gap_id, accepted_values=segment.accepted_values))
                segments.append(NativeGapSegment(gap_id=gap_id))
            elif segment.text:
                segments.append(NativeTextSegment(text=segment.text))
        if segments:
            body.append(NativeParagraph(segments=tuple(segments)))
    match_left = tuple(
        NativeMatchLeft(left_id=f"left_{index:03d}", text=text)
        for index, text in enumerate(produced.match_left, start=1)
    )
    match_right = tuple(
        NativeMatchRight(right_id=f"right_{index:03d}", text=text)
        for index, text in enumerate(produced.match_right, start=1)
    )
    left_ids = {entry.text: entry.left_id for entry in match_left}
    right_ids = {entry.text: entry.right_id for entry in match_right}
    pairs = tuple(
        NativeMatchPair(left_id=left_ids[pair.left], right_id=right_ids[pair.right])
        for pair in produced.match_pairs
    )
    keyed = bool(correct) or bool(pairs) or any(gap.accepted_values for gap in gaps)
    if produced.kind is NativeExamItemKind.FREE_TEXT:
        origin = NativeAnswerKeyOrigin.NOT_APPLICABLE
    else:
        origin = NativeAnswerKeyOrigin.SOURCE_PROVIDED if keyed else NativeAnswerKeyOrigin.ABSENT
    return NativeExamItem(
        item_id="item_001",
        sequence=1,
        kind=produced.kind,
        title=produced.title,
        printed_label=produced.printed_label,
        body=tuple(body),
        points=produced.points,
        choices=choices,
        gaps=tuple(gaps),
        match_left=match_left,
        match_right=match_right,
        answer_key=NativeAnswerKey(origin=origin, correct_choice_ids=correct, match_pairs=pairs),
        marking_guide=(
            produced.marking_guide if produced.kind is NativeExamItemKind.FREE_TEXT else None
        ),
        review=NativeItemReview(
            state=NativeItemReviewState.REVIEW_COMPLETE,
            parse_origin=NativeParseOrigin.LLM_PARSED,
        ),
        source_anchor=produced.source_anchors[0],
    )


def review_source_item(chunks: tuple[DocxChunk, ...], reason: str) -> NativeExamItem:
    """One teacher-review item holding the plain source text of ``chunks``, one paragraph per
    chunk in source order, whatever the model wrote."""
    return NativeExamItem(
        item_id="item_001",
        sequence=1,
        kind=NativeExamItemKind.FREE_TEXT,
        body=tuple(
            NativeParagraph(segments=(NativeTextSegment(text=chunk.text),))
            for chunk in chunks
            if chunk.text
        )
        or (NativeParagraph(segments=(NativeTextSegment(text="Tomt källstycke."),)),),
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
        review=NativeItemReview(
            state=NativeItemReviewState.REVIEW_REQUIRED,
            parse_origin=NativeParseOrigin.DETERMINISTIC,
            reasons=(reason,),
        ),
        source_anchor=chunks[0].anchor,
    )


def review_chunk_item(chunk: DocxChunk, reason: str) -> NativeExamItem:
    return review_source_item((chunk,), reason)


def _ordered_items(
    chunks: tuple[DocxChunk, ...],
    accepted: tuple[tuple[NativeExamItem, tuple[str, ...]], ...],
    review_reasons: dict[str, str],
    instructions: tuple[ProducedMetadata, ...],
    governed: Mapping[str, frozenset[str]],
) -> SectionInstructions:
    positions = {c.anchor: i for i, c in enumerate(chunks)}
    ordered = [(min(positions[a] for a in anchors), anchors, item) for item, anchors in accepted]
    ordered.extend(
        (
            positions[chunk.anchor],
            (chunk.anchor,),
            review_chunk_item(chunk, review_reasons[chunk.anchor]),
        )
        for chunk in chunks
        if chunk.anchor in review_reasons
    )
    ordered.sort(key=lambda entry: entry[0])
    return place_section_instructions(chunks, ordered, instructions, governed)


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
    governed: Mapping[str, frozenset[str]] = NOTHING_GOVERNED,
    events: tuple[DocxBuildEvent, ...] = (),
    input_tokens: int | None = None,
    output_tokens: int | None = None,
) -> DocxBuildResult:
    """Keep facit chunks as teacher notes and every unbuilt chunk as a review item."""
    if not chunks:
        empty = "Dokumentet saknar läsbart innehåll."
        chunks = (DocxChunk("empty", "paragraph", empty, empty),)
        review_reasons = {"empty": "Dokumentet saknar läsbart innehåll."}
    placed = _ordered_items(chunks, accepted, review_reasons, instructions, governed)
    items = placed.items
    notes = [chunk.text for chunk in chunks if chunk.anchor in key_anchors]
    notes.extend(dict.fromkeys(reason for item in items for reason in item.review.reasons))
    if title is not None:
        document_title = title.text
    else:
        stem, extension = (
            (filename[:-5], filename[-5:]) if filename.lower().endswith(".docx") else (filename, "")
        )
        document_title = title_without_answer_key(stem, filename=True) + extension
    document = NativeExamDocument(
        document_id=document_id,
        revision=1,
        title=document_title,
        instructions=tuple(v.text for i, v in enumerate(instructions) if i not in placed.reaching),
        items=items,
        parents=placed.parents,
        origin=NativeExamDocumentOrigin(
            kind="docx_import",
            source_filename=filename,
            source_sha256=source_sha256,
            extractor_version="docx_ai_build_v2",
        ),
    )
    return DocxBuildResult(document, tuple(notes), input_tokens, output_tokens, events)
