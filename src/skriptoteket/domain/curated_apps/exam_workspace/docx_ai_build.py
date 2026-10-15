"""Map produced items to the native contract and assemble the build result."""

import hashlib
from collections.abc import Iterable, Mapping
from decimal import Decimal
from types import MappingProxyType
from uuid import UUID

from skriptoteket.domain.curated_apps.exam_workspace.answer_spelling import (
    filter_answer_spelling_candidates,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
    DocxBuildEvent,
    DocxBuildResult,
    ProducedItem,
    ProducedMetadata,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_scoring import (
    free_text_criteria,
    matching_score,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import (
    DocxChunk,
    DocxImage,
    DocxMissingImage,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_governing_chunks import (
    release_governing_chunks,
    unclaimed_governing,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_instruction_runs import (
    heading_wording,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_own_instructions import (
    return_misplaced_own_chunks,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_section_instructions import (
    SectionInstructions,
    place_section_instructions,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import (
    printed_points,
    title_without_answer_key,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeAssetSegment,
    NativeGapSegment,
    NativeParagraph,
    NativeSegment,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_criteria import (
    NativeExamCriterion,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamAsset,
    NativeExamDocument,
    NativeExamDocumentOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
    NativeExamItem,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_matching import (
    NativeMatchLeft,
    NativeMatchPair,
    NativeMatchRight,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeAnswerKey,
    NativeChoice,
    NativeGap,
    NativeItemReview,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
    NativeItemReviewState,
    NativeParseOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import (
    body_asset_ids,
    body_plain_text,
    source_paragraphs,
)

_BLANK = NativeTextSegment(text="____")


# No shared context governs two or more questions: every instruction is placed by its run.
NOTHING_GOVERNED: Mapping[str, frozenset[str]] = MappingProxyType({})


def _missing_picture_reason(missing: DocxMissingImage) -> str:
    return (
        f"Bilden {missing.reference} ({missing.media_type}) kan inte visas i provet. "
        "Granska frågan manuellt."
    )


def missing_picture_reasons(chunks: Iterable[DocxChunk]) -> tuple[str, ...]:
    """One named Swedish review reason per picture the chunker could not turn into an image.

    The same picture referenced twice is one reason. An empty result means no chunk in
    ``chunks`` carries a picture the conversion could not show.
    """
    reasons: dict[str, str] = {}
    for chunk in chunks:
        for missing in chunk.missing_images:
            reasons.setdefault(missing.reference, _missing_picture_reason(missing))
    return tuple(reasons.values())


def native_item(produced: ProducedItem, *, chunks: Iterable[DocxChunk] = ()) -> NativeExamItem:
    """Assign IDs and provenance; the native contract raises on any invalid shape.

    An asset segment becomes a native picture reference only when its id belongs to one of
    the provided source chunks; a model-invented id raises, so admission falls back to the
    question's own source. The same picture may repeat; references are never deduplicated.
    A chunk with a picture the conversion could not show raises before anything else: no
    picture may vanish from the question, so admission falls back to its source review.
    """
    chunk_list = tuple(chunks)
    unresolved = tuple(
        dict.fromkeys(missing.reference for chunk in chunk_list for missing in chunk.missing_images)
    )
    if unresolved:
        raise ValueError(f"unresolved source pictures: {', '.join(unresolved)}")
    known_assets = {image.asset_id for chunk in chunk_list for image in chunk.images}
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
            if segment.kind == "asset":
                asset_id = segment.asset_id
                if asset_id is None or asset_id not in known_assets:
                    raise ValueError(f"unknown source picture {asset_id}")
                segments.append(NativeAssetSegment(asset_id=asset_id))
            elif segment.kind == "gap" and produced.kind is not NativeExamItemKind.GAP_FILL:
                # Only gap_fill answers in a gap; another kind shows a printed blank as text.
                segments.append(_BLANK)
            elif segment.kind == "gap":
                gap_id = f"gap_{len(gaps) + 1:03d}"
                automatic = (
                    filter_answer_spelling_candidates(
                        segment.accepted_values, segment.spelling_candidates
                    )
                    if produced.key_source in {"copied", "interpreted"}
                    else ()
                )
                gaps.append(
                    NativeGap(
                        gap_id=gap_id,
                        accepted_values=segment.accepted_values,
                        automatic_values=automatic,
                    )
                )
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
    if produced.kind is NativeExamItemKind.MATCHING:
        if pairs:
            tick_points, derived_points, points_estimated = matching_score(
                produced.points, len(pairs)
            )
            points: int | float | None = (
                int(derived_points) if derived_points == int(derived_points) else derived_points
            )
        else:
            # An unkeyed grid keeps the default tick for the editor and no points,
            # because zero ticks can never equal a positive total.
            tick_points, points, points_estimated = Decimal(1), None, False
    else:
        tick_points, points, points_estimated = None, produced.points, False
    if produced.kind is NativeExamItemKind.FREE_TEXT:
        origin = NativeAnswerKeyOrigin.NOT_APPLICABLE
    else:
        origins = {
            "copied": NativeAnswerKeyOrigin.SOURCE_PROVIDED,
            "interpreted": NativeAnswerKeyOrigin.AI_INTERPRETED,
            "invented": NativeAnswerKeyOrigin.MACHINE_PROPOSED,
        }
        origin = (
            origins[produced.key_source]
            if keyed and produced.key_source is not None
            else NativeAnswerKeyOrigin.ABSENT
        )
    criteria: tuple[NativeExamCriterion, ...] = ()
    if produced.kind is NativeExamItemKind.FREE_TEXT:
        criteria, points, points_estimated = free_text_criteria(produced)
    return NativeExamItem(
        item_id="item_001",
        sequence=1,
        kind=produced.kind,
        printed_label=produced.printed_label,
        facit_text=produced.facit_text,
        body=tuple(body),
        points=points,
        points_estimated=points_estimated,
        tick_points=tick_points,
        choices=choices,
        gaps=tuple(gaps),
        match_left=match_left,
        match_right=match_right,
        answer_key=NativeAnswerKey(origin=origin, correct_choice_ids=correct, match_pairs=pairs),
        criteria=criteria,
        review=NativeItemReview(
            state=NativeItemReviewState.REVIEW_COMPLETE,
            parse_origin=NativeParseOrigin.LLM_PARSED,
        ),
        source_anchor=produced.source_anchors[0],
    )


def review_source_item(chunks: tuple[DocxChunk, ...], reason: str) -> NativeExamItem:
    """One teacher-review item holding the plain source text of ``chunks``, one paragraph per
    chunk in source order, whatever the model wrote; it keeps the question's printed points
    and every picture at its exact place in the chunk's text, and names every picture the
    conversion could not show beside the caller's ``reason``."""
    body = source_paragraphs(chunks)
    return NativeExamItem(
        item_id="item_001",
        sequence=1,
        kind=NativeExamItemKind.FREE_TEXT,
        points=printed_points(chunks),
        body=body or (NativeParagraph(segments=(NativeTextSegment(text="Tomt källstycke."),)),),
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
        review=NativeItemReview(
            state=NativeItemReviewState.REVIEW_REQUIRED,
            parse_origin=NativeParseOrigin.DETERMINISTIC,
            reasons=(reason, *missing_picture_reasons(chunks)),
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
    title_anchors: frozenset[str] = frozenset(),
    own_anchors: frozenset[str] = frozenset(),
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
    return place_section_instructions(
        chunks, ordered, instructions, governed, title_anchors, own_anchors
    )


def asset_manifest(
    items: Iterable[NativeExamItem],
    chunks: Iterable[DocxChunk],
    *,
    shared_bodies: Iterable[tuple[NativeParagraph, ...]] = (),
) -> tuple[tuple[NativeExamAsset, ...], Mapping[str, bytes]]:
    """The pictures the document references: native metadata and payloads, in asset-id order.

    Every picture an item's student body references, every picture a shared instruction
    body places at its source position (a parent or the document-global instruction), and
    every picture an item's stored retry source keeps (facit and read-only context
    included) is carried, because the native contract rejects an orphan asset; the QTI
    export reads the body references only, so a source-only picture never reaches a
    student. The container requires payloads to match the document's asset list exactly.
    """
    images: dict[str, DocxImage] = {}
    for chunk in chunks:
        for image in chunk.images:
            images.setdefault(image.asset_id, image)
    referenced = sorted(
        {
            asset_id
            for item in items
            for asset_id in (*item.body_asset_ids(), *item.source_asset_ids())
        }
        | {asset_id for body in shared_bodies for asset_id in body_asset_ids(body)}
    )
    missing = [asset_id for asset_id in referenced if asset_id not in images]
    if missing:
        raise ValueError(f"items reference unknown source pictures: {', '.join(missing)}")
    assets = tuple(
        NativeExamAsset(
            asset_id=asset_id,
            sha256=hashlib.sha256(images[asset_id].payload).hexdigest(),
            media_type=images[asset_id].media_type,
            byte_length=len(images[asset_id].payload),
            width=images[asset_id].width,
            height=images[asset_id].height,
        )
        for asset_id in referenced
    )
    payloads = {asset_id: images[asset_id].payload for asset_id in referenced}
    return assets, MappingProxyType(payloads)


def _instruction_paragraphs(
    instruction: ProducedMetadata, by_anchor: Mapping[str, DocxChunk]
) -> tuple[NativeParagraph, ...]:
    """The document-global instruction's admitted wording, pictures at their source place.

    The converter copies each instruction from its source chunk, sometimes without a
    printed points label a heading carries; a source whose wording equals the admitted
    wording either way keeps every picture at its exact source place. A wording the
    converter changed leaves its pictures without a truthful place, so it is refused
    instead of dropping them or moving them silently.
    """
    sources = tuple(by_anchor[a] for a in instruction.source_anchors if a in by_anchor)
    raw = source_paragraphs(sources)
    if body_plain_text(raw) == instruction.text:
        return raw
    normalized = source_paragraphs(
        DocxChunk(
            chunk.anchor,
            chunk.kind,
            heading_wording(chunk, None),
            chunk.marked_text,
        )
        if chunk.kind == "heading"
        else chunk
        for chunk in sources
    )
    if body_plain_text(normalized) == instruction.text:
        # The source's pictured wording is canonical: removing a printed heading
        # prefix would invalidate the pixel-relative offsets. Keep it verbatim.
        return raw if any(chunk.images or chunk.missing_images for chunk in sources) else normalized
    if body_asset_ids(raw):
        raise ValueError(
            f"instruction pictures have no faithful place: {instruction.source_anchors}"
        )
    return (NativeParagraph(segments=(NativeTextSegment(text=instruction.text),)),)


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
    questions: tuple[tuple[str, ...], ...] = (),
    events: tuple[DocxBuildEvent, ...] = (),
    input_tokens: int | None = None,
    output_tokens: int | None = None,
) -> DocxBuildResult:
    """Keep facit chunks as teacher notes and every unbuilt chunk as a review item; a governing
    chunk an item lists or no entry holds becomes an instruction for its section parent (D40).

    ``questions`` holds each grouped question's own anchors. An own chunk listed as an
    instruction that placement does not put at its question goes back to its question's item,
    and placement runs again without it (D42).
    """
    if not chunks:
        empty = "Dokumentet saknar läsbart innehåll."
        chunks = (DocxChunk("empty", "paragraph", empty, empty),)
        review_reasons = {"empty": "Dokumentet saknar läsbart innehåll."}
    unclaimed, review_reasons = unclaimed_governing(chunks, review_reasons, governed)
    instructions = (*instructions, *unclaimed)
    released = release_governing_chunks(chunks, accepted, instructions, governed)
    accepted, instructions = released.accepted, released.instructions
    events = (*events, *released.events)
    title_anchors = frozenset(title.source_anchors) if title is not None else frozenset()
    own_anchors = frozenset(anchor for own in questions for anchor in own)
    placed = _ordered_items(
        chunks, accepted, review_reasons, instructions, governed, title_anchors, own_anchors
    )
    while returned := return_misplaced_own_chunks(
        chunks, accepted, instructions, placed.landed, questions, governed
    ):
        accepted, instructions = returned.accepted, returned.instructions
        events = (*events, *returned.events)
        placed = _ordered_items(
            chunks, accepted, review_reasons, instructions, governed, title_anchors, own_anchors
        )
    items = placed.items
    by_anchor = {chunk.anchor: chunk for chunk in chunks}
    global_instructions = tuple(
        paragraph
        for index, instruction in enumerate(instructions)
        if index not in placed.landed
        for paragraph in _instruction_paragraphs(instruction, by_anchor)
    )
    shared_bodies = (
        *(parent.instruction for parent in placed.parents),
        global_instructions,
    )
    assets, assets_by_id = asset_manifest(items, chunks, shared_bodies=shared_bodies)
    # Document-level notes only: each item shows its own reasons (D8).
    notes = [chunk.text for chunk in chunks if chunk.anchor in key_anchors]
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
        instructions=global_instructions,
        items=items,
        parents=placed.parents,
        assets=assets,
        origin=NativeExamDocumentOrigin(
            kind="docx_import",
            source_filename=filename,
            source_sha256=source_sha256,
            extractor_version="docx_ai_build_v2",
        ),
    )
    return DocxBuildResult(
        document, tuple(notes), input_tokens, output_tokens, events, assets_by_id=assets_by_id
    )
