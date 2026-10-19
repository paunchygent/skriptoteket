"""Assemble aligned items into the build result."""

from collections.abc import Mapping
from types import MappingProxyType
from uuid import UUID

from skriptoteket.domain.curated_apps.exam_workspace import docx_build_assets
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
    DocxBuildEvent,
    DocxBuildResult,
    ProducedMetadata,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_answer_line_gate import (
    gated_item,
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
    aligned_source_item,
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
    review_source_item,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import (
    title_without_answer_key,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
    NativeExamDocumentOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
    NativeExamItem,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import (
    is_answer_line_chunk,
    without_printed_answer_lines,
)

# No shared context governs two or more questions: every instruction is placed by its run.
NOTHING_GOVERNED: Mapping[str, frozenset[str]] = MappingProxyType({})


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
        if chunk.anchor in review_reasons and not is_answer_line_chunk(chunk)
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
    # The one W10 gate on the final document: no printed answer line reaches any item
    # body, parent instruction or document instruction, whichever path rebuilt it.
    items = tuple(gated_item(item, by_anchor) for item in scored.items)
    parents = tuple(
        parent.model_copy(update={"instruction": without_printed_answer_lines(parent.instruction)})
        for parent in scored.parents
    )
    events = (*events, *scored.events)
    document_instructions = global_instructions(
        chunks,
        tuple(m for index, m in enumerate(instructions) if index not in placed.landed),
        exam_instructions,
        by_anchor,
    )
    document_instructions = without_printed_answer_lines(document_instructions)
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
