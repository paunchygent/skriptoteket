"""Map produced items to the native contract and assemble the build result."""

import re
from collections.abc import Callable, Iterable, Mapping, Sequence
from decimal import Decimal
from types import MappingProxyType
from uuid import UUID

from skriptoteket.domain.curated_apps.exam_workspace import docx_build_assets
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
    DocxBuildEvent,
    DocxBuildResult,
    ProducedItem,
    ProducedMetadata,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_gap_values import native_gap
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_scoring import (
    free_text_criteria,
    matching_score,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import (
    DocxChunk,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_document_instructions import (
    exam_wide_instructions,
    global_instructions,
    placement_chunks,
    placement_exclusions,
    without_excluded,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_governing_chunks import (
    release_governing_chunks,
    unclaimed_governing,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_item_alignment import (
    Accepted,
    AlignedItem,
    aligned_source_item,
    entry_chunks,
    paragraph_chunks,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_own_instructions import (
    return_misplaced_own_chunks,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_points_lines import (
    NO_PART_LINES,
    NO_PRINTED_POINTS,
    PartLines,
    PrintedPoints,
    part_lines,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_section_instructions import (
    SectionInstructions,
    place_section_instructions,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_section_points import (
    apply_printed_points,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_review import (
    missing_picture_reasons as missing_picture_reasons,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_review import (
    review_source_item as review_source_item,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import (
    title_without_answer_key,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_document_language import (
    Language,
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
from skriptoteket.domain.curated_apps.exam_workspace.source_entry_ownership import (
    produced_entry_body,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_format_coverage import (
    NativeSourceEntry,
    complete_source_formatting,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_formatting import (
    FormattingTransferError,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_item_formatting import (
    item_source_formatting,
)

_BLANK = NativeTextSegment(text="____", marks=())

# No shared context governs two or more questions: every instruction is placed by its run.
NOTHING_GOVERNED: Mapping[str, frozenset[str]] = MappingProxyType({})

_ITALIC_TAG = re.compile(r"</?i>")


def aligned_native_item(
    produced: ProducedItem,
    *,
    chunks: Iterable[DocxChunk] = (),
    foreign_chunks: Sequence[DocxChunk],
    language: Language,
    formatting_observer: Callable[[str], None] | None = None,
) -> AlignedItem:
    """Assign IDs and provenance; the native contract raises on any invalid shape.

    The result names, per body paragraph, the source chunk that paragraph shows: the one
    alignment the source formatting made, never a second reading of the wording. A paragraph
    whose text is another question's source is not this item's content: ``foreign_chunks``
    holds the other questions' own chunks, and such a paragraph is rebuilt from this item's
    source instead (TASK-SKRIPT-39-04-15 D4).

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
    formatting = item_source_formatting(produced, chunk_list, foreign_chunks=foreign_chunks)
    choices = tuple(
        NativeChoice(choice_id=f"choice_{index:03d}", body=produced_entry_body(choice.text))
        for index, choice in enumerate(produced.choices, start=1)
    )
    correct = tuple(
        native.choice_id
        for native, choice in zip(choices, produced.choices, strict=True)
        if choice.correct
    )
    gaps: list[NativeGap] = []
    body: list[NativeParagraph] = []
    gold_answers = tuple(
        value
        for paragraph in produced.body
        for segment in paragraph.segments
        if segment.kind == "gap"
        for value in segment.accepted_values
    )
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
                gaps.append(
                    native_gap(
                        segment,
                        gap_id=gap_id,
                        language=language,
                        item_gold_answers=gold_answers,
                    )
                )
                segments.append(NativeGapSegment(gap_id=gap_id))
            elif segment.text:
                segments.append(NativeTextSegment(text=segment.text, marks=()))
        if segments:
            body.append(NativeParagraph(heading_level=None, segments=tuple(segments)))
    body_source = formatting.body
    answers = {gap.gap_id: gap.accepted_values for gap in gaps}
    can_rebuild_body = not known_assets
    try:
        formatted_body = body_source.body(body, answers=answers)
    except FormattingTransferError:
        if not can_rebuild_body:
            raise
        # Identified text-only source can recover the whole body when no individual
        # paragraph wins alignment. Only a genuinely failed source rebuild escapes.
        formatted_body = body_source.rebuild_body(answers)
    match_left = tuple(
        NativeMatchLeft(left_id=f"left_{index:03d}", body=produced_entry_body(text))
        for index, text in enumerate(produced.match_left, start=1)
    )
    match_right = tuple(
        NativeMatchRight(right_id=f"right_{index:03d}", body=produced_entry_body(text))
        for index, text in enumerate(produced.match_right, start=1)
    )
    left_ids = {
        text: entry.left_id for text, entry in zip(produced.match_left, match_left, strict=True)
    }
    right_ids = {
        text: entry.right_id for text, entry in zip(produced.match_right, match_right, strict=True)
    }
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
    sources = formatting.sources
    choices = formatting.restore("choices", choices)
    match_left = formatting.restore("match_left", match_left)
    match_right = formatting.restore("match_right", match_right)
    formatted_body = complete_source_formatting(
        chunk_list,
        sources,
        body_source,
        formatted_body,
        printed_label=produced.printed_label,
        answers=answers,
        can_rebuild_body=can_rebuild_body,
        entries=(
            NativeSourceEntry(surface.sequence, ordinal, start, end)
            for surface in formatting.surfaces
            for ordinal, (start, end) in enumerate(surface.source.entry_spans, start=1)
        ),
    )
    if formatting_observer is not None:
        paths = {source.path for source in sources}
        formatting_observer(
            "rebuilt" if "rebuilt" in paths else "aligned" if "aligned" in paths else "exact"
        )
    item = NativeExamItem(
        item_id="item_001",
        sequence=1,
        kind=produced.kind,
        printed_label=produced.printed_label,
        # The source's italic tags mark formatting for the model, never the teacher's wording.
        facit_text=_ITALIC_TAG.sub("", produced.facit_text) if produced.facit_text else None,
        body=formatted_body,
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
    entries = frozenset().union(
        *(
            entry_chunks(surface.source, surface.source.entry_spans)
            for surface in formatting.surfaces
        )
    )
    return AlignedItem(item, paragraph_chunks(body_source), entries)


def review_chunk_item(chunk: DocxChunk, reason: str) -> NativeExamItem:
    return review_source_item((chunk,), reason)


def _ordered_items(
    chunks: tuple[DocxChunk, ...],
    accepted: Accepted,
    review_reasons: dict[str, str],
    instructions: tuple[ProducedMetadata, ...],
    governed: Mapping[str, frozenset[str]],
    title_anchors: frozenset[str] = frozenset(),
    own_anchors: frozenset[str] = frozenset(),
    parts: PartLines = NO_PART_LINES,
) -> SectionInstructions:
    positions = {c.anchor: i for i, c in enumerate(chunks)}
    ordered = [(min(positions[a] for a in anchors), anchors, item) for item, anchors in accepted]
    ordered.extend(
        (
            positions[chunk.anchor],
            (chunk.anchor,),
            aligned_source_item(review_chunk_item(chunk, review_reasons[chunk.anchor]), (chunk,)),
        )
        for chunk in chunks
        if chunk.anchor in review_reasons
    )
    ordered.sort(key=lambda entry: entry[0])
    return place_section_instructions(
        chunks,
        ordered,
        instructions,
        governed,
        title_anchors,
        own_anchors,
        parts,
    )


def assemble_build_result(
    *,
    document_id: UUID,
    filename: str,
    source_sha256: str,
    chunks: tuple[DocxChunk, ...],
    accepted: Accepted = (),
    review_reasons: dict[str, str],
    key_anchors: frozenset[str] = frozenset(),
    title: ProducedMetadata | None = None,
    instructions: tuple[ProducedMetadata, ...] = (),
    governed: Mapping[str, frozenset[str]] = NOTHING_GOVERNED,
    exam_wide: frozenset[str] = frozenset(),
    exam_metadata: frozenset[str] = frozenset(),
    questions: tuple[tuple[str, ...], ...] = (),
    printed: PrintedPoints = NO_PRINTED_POINTS,
    events: tuple[DocxBuildEvent, ...] = (),
    input_tokens: int | None = None,
    output_tokens: int | None = None,
) -> DocxBuildResult:
    """Keep facit chunks as teacher notes and every unbuilt chunk as a review item; a governing
    chunk an item lists or no entry holds becomes an instruction for its section parent (D40).

    ``questions`` holds each grouped question's own anchors. An own chunk listed as an
    instruction that placement does not put at its question goes back to its question's item,
    and placement runs again without it (D42). ``printed`` owns every printed total; it
    scores the placed items once (``apply_printed_points``).

    ``exam_wide`` holds the anchors of exam-wide text and of exam metadata; ``exam_metadata``
    is the metadata subset. No batch claims them. Exam-wide text is never placed: each chunk
    joins the document's instructions once, from its own source text, and is never an item
    body, parent or review item. Metadata lines go nowhere. These anchors and every printed
    total the points plan classifies as metadata (``printed.metadata``) are kept out of
    placement: no instruction holds them and no heading of theirs opens, joins or ends a run.
    """
    if not chunks:
        empty = "Dokumentet saknar läsbart innehåll."
        chunks = (DocxChunk("empty", "paragraph", empty, empty),)
        review_reasons = {"empty": "Dokumentet saknar läsbart innehåll."}
    by_anchor = {chunk.anchor: chunk for chunk in chunks}
    excluded = placement_exclusions(exam_wide, exam_metadata, printed.metadata)
    exam_instructions = exam_wide_instructions(chunks, exam_wide, exam_metadata, printed.metadata)
    review_reasons = {a: r for a, r in review_reasons.items() if a not in excluded}
    unclaimed, review_reasons = unclaimed_governing(chunks, review_reasons, governed)
    instructions = (*instructions, *unclaimed)
    released = release_governing_chunks(chunks, accepted, instructions, governed)
    accepted = released.accepted
    # No excluded chunk is a review item or an instruction, and placement sees only the
    # excluded chunks an item holds as its own.
    instructions = without_excluded(released.instructions, excluded, by_anchor)
    placeable = placement_chunks(chunks, excluded, accepted)
    events = (*events, *released.events)
    title_anchors = frozenset(title.source_anchors) if title is not None else frozenset()
    own_anchors = frozenset(anchor for own in questions for anchor in own)
    parts = part_lines(printed.parts)
    placed = _ordered_items(
        placeable,
        accepted,
        review_reasons,
        instructions,
        governed,
        title_anchors,
        own_anchors,
        parts,
    )
    while returned := return_misplaced_own_chunks(
        chunks, accepted, instructions, placed.landed, questions, governed
    ):
        accepted, instructions = returned.accepted, returned.instructions
        events = (*events, *returned.events)
        placed = _ordered_items(
            placeable,
            accepted,
            review_reasons,
            instructions,
            governed,
            title_anchors,
            own_anchors,
            parts,
        )
    scored = apply_printed_points(placed.items, placed.parents, printed, by_anchor)
    items, parents = scored.items, scored.parents
    events = (*events, *scored.events)
    document_instructions = global_instructions(
        chunks,
        tuple(m for index, m in enumerate(instructions) if index not in placed.landed),
        exam_instructions,
        by_anchor,
    )
    shared_bodies = (
        *(parent.instruction for parent in parents),
        document_instructions,
    )
    assets, assets_by_id = docx_build_assets.asset_manifest(
        items, chunks, shared_bodies=shared_bodies
    )
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
        instructions=document_instructions,
        items=items,
        parents=parents,
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
