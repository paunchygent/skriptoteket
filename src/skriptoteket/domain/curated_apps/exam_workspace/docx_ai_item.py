"""Map one produced reply item to one aligned native item."""

import re
from collections.abc import Callable, Iterable, Sequence
from decimal import Decimal

from skriptoteket.domain.curated_apps.exam_conversion.exam_print_house_template import (
    DEFAULT_WRITING_LINES,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
    ProducedItem,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_gap_values import native_gap
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_scoring import (
    free_text_criteria,
    matching_score,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import (
    DocxChunk,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_item_alignment import (
    AlignedItem,
    entry_chunks,
    paragraph_chunks,
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
    is_printed_answer_line,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_entry_ownership import (
    produced_entry_body,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_format_coverage import (
    NativeSourceEntry,
    complete_source_formatting,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_format_errors import (
    FormattingTransferError,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_gap_paragraphs import (
    gap_paragraphs_from_source,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_item_formatting import (
    item_source_formatting,
)

_BLANK = NativeTextSegment(text="____", marks=())

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
        if segments and not is_printed_answer_line(segments):
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
    if produced.kind is NativeExamItemKind.GAP_FILL:
        formatted_body = gap_paragraphs_from_source(body_source, formatted_body)
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
        # The reply's printed reading, filled from the question's own label upstream;
        # matching and rubric derivation change points but never this printed value.
        source_points=produced.points,
        tick_points=tick_points,
        writing_lines=(
            DEFAULT_WRITING_LINES if produced.kind is NativeExamItemKind.FREE_TEXT else None
        ),
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
