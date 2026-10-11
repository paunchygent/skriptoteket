"""Map produced items to the native contract and assemble the build result."""

import re
from collections.abc import Iterator, Sequence
from uuid import UUID

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
    DocxBuildEvent,
    DocxBuildResult,
    ProducedItem,
    ProducedMetadata,
    ProducedParagraph,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import (
    POINT_LABEL,
    defined_terms,
    points_line,
    uses_term,
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

_REVIEW_BLANK = NativeTextSegment(text="____")


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
        body=tuple(body),
        points=produced.points,
        choices=choices,
        gaps=tuple(gaps),
        match_left=match_left,
        match_right=match_right,
        answer_key=NativeAnswerKey(origin=origin, correct_choice_ids=correct, match_pairs=pairs),
        review=NativeItemReview(
            state=NativeItemReviewState.REVIEW_COMPLETE,
            parse_origin=NativeParseOrigin.LLM_PARSED,
        ),
        source_anchor=produced.source_anchors[0],
    )


def _review_segments(paragraph: ProducedParagraph) -> Iterator[NativeSegment]:
    for segment in paragraph.segments:
        if segment.kind == "gap":
            yield _REVIEW_BLANK
        elif segment.text:
            yield NativeTextSegment(text=segment.text)


def review_item(produced: ProducedItem, reason: str) -> NativeExamItem:
    """One teacher-review item for a question the model could not convert.

    Gap answers, choice keys and match pairs never become text; a gap shows as a blank line.
    """
    paragraphs = [
        NativeParagraph(segments=segments)
        for paragraph in produced.body
        if (segments := tuple(_review_segments(paragraph)))
    ]
    if produced.choices:
        lines = "\n".join(f"{chr(ord('A') + i)}. {c.text}" for i, c in enumerate(produced.choices))
        paragraphs.append(NativeParagraph(segments=(NativeTextSegment(text=lines),)))
    for entries in (produced.match_left, produced.match_right):
        if entries:
            lines = "\n".join(entries)
            paragraphs.append(NativeParagraph(segments=(NativeTextSegment(text=lines),)))
    return NativeExamItem(
        item_id="item_001",
        sequence=1,
        kind=NativeExamItemKind.FREE_TEXT,
        title=produced.title,
        body=tuple(paragraphs),
        points=produced.points,
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
        review=NativeItemReview(
            state=NativeItemReviewState.REVIEW_REQUIRED,
            parse_origin=NativeParseOrigin.LLM_PARSED,
            reasons=(reason,),
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


_Placed = tuple[int, tuple[str, ...], NativeExamItem]


def _item_text(item: NativeExamItem) -> str:
    return " ".join(" ".join((item.title or "", *item.plain_text_lines())).split())


def _with_paragraphs(item: NativeExamItem, texts: list[str], *, first: bool) -> NativeExamItem:
    shown = _item_text(item)
    added = tuple(
        NativeParagraph(segments=(NativeTextSegment(text=text),))
        for text in dict.fromkeys(texts)
        if " ".join(text.split()) not in shown
    )
    body = (*added, *item.body) if first else (*item.body, *added)
    return item.model_copy(update={"body": body})


def _lead_in_labels(chunks: tuple[DocxChunk, ...], lead_in: set[int], own: set[str]) -> set[int]:
    """Headings that label a stretch of an instruction lead-in, such as one passage of two.

    Such a heading prints no points and sits between instruction paragraphs that no item owns.
    """
    return {
        i
        for i in range(1, len(chunks) - 1)
        if chunks[i].kind == "heading"
        and chunks[i].anchor not in own
        and not POINT_LABEL.search(chunks[i].text)
        and {i - 1, i + 1} <= lead_in
        and chunks[i - 1].kind != "heading"
        and chunks[i + 1].kind != "heading"
    }


# A question line that starts with its printed number.
_NUMBERED = re.compile(r"^\s*\d{1,3}[.)]\s")
# A question line that opens with quoted material, after any list label.
_OPENS_WITH_QUOTE = re.compile(r"^\s*(?:\w{1,3}[.)]\s*)?[\"\u201c\u2018\u00ab\u201e]")


def _is_lead_in(chunk: DocxChunk) -> bool:
    return chunk.kind != "heading" and chunk.text.rstrip().endswith(":")


def _opens_with_quote(sources: Sequence[DocxChunk]) -> bool:
    """Whether the question's first own line after any heading and lead-in opens with a quote."""
    first = next((c for c in sources if c.kind != "heading" and not _is_lead_in(c)), None)
    return first is not None and bool(_OPENS_WITH_QUOTE.match(first.text))


def _with_section_instructions(
    chunks: tuple[DocxChunk, ...],
    ordered: list[_Placed],
    instructions: tuple[ProducedMetadata, ...],
) -> list[_Placed]:
    """Place instruction text into the items it belongs to; Exam.net carries only items.

    An instruction printed inside an item's own chunks joins that item. Any other instruction
    opens every item of its run, which ends at the next section heading (a heading no item
    owns, other than a lead-in label) or at the next instruction printed after one of the
    run's items. Section headings and points lines are structure and are never carried. An
    instruction that defines terms reaches only the run's items whose own chunks use one.
    Lines an item prints before its numbered question line are such an instruction too. A
    lead-in ending in a colon that introduces a question opening with quoted material
    reaches only the run's items that open with quotes.
    """
    positions = {c.anchor: i for i, c in enumerate(chunks)}
    own = {anchor for _, anchors, _ in ordered for anchor in anchors}
    item_sources = [
        [chunks[i] for i in sorted(positions[a] for a in anchors)] for _, anchors, _ in ordered
    ]
    spans = [(positions[s[0].anchor], positions[s[-1].anchor]) for s in item_sources]
    joined: dict[int, list[str]] = {}
    runs: list[tuple[int, tuple[DocxChunk, ...]]] = []
    for instruction in instructions:
        at = sorted(positions[a] for a in instruction.source_anchors)
        sources = tuple(chunks[i] for i in at)
        owner = next((k for k, (lo, hi) in enumerate(spans) if lo < at[0] and at[-1] < hi), None)
        if owner is not None:
            joined.setdefault(owner, []).extend(chunk.text for chunk in sources)
        else:
            runs.append((at[-1], sources))
    for item_chunks in item_sources:
        lines = [c for c in item_chunks if c.kind != "heading"]
        numbered = next((i for i, c in enumerate(lines) if _NUMBERED.match(c.text)), 0)
        if numbered:
            runs.append((positions[lines[numbered - 1].anchor], tuple(lines[:numbered])))
    lead_in = {
        positions[c.anchor] for _, sources in runs for c in sources if not points_line(c.text)
    }
    labels = _lead_in_labels(chunks, lead_in, own)
    boundaries = [
        i
        for i, chunk in enumerate(chunks)
        if chunk.kind == "heading" and chunk.anchor not in own and i not in labels
    ]
    starts = sorted(start for start, _ in runs)
    carried: dict[int, list[str]] = {}
    for start, grouped in sorted(runs, key=lambda run: run[0]):
        sources = tuple(
            c
            for c in grouped
            if not points_line(c.text) and (c.kind != "heading" or positions[c.anchor] in labels)
        )
        if not sources:
            continue
        following = [k for k, (position, _, _) in enumerate(ordered) if position >= start]
        first_item = next((ordered[k][0] for k in following if ordered[k][0] > start), len(chunks))
        end = min(
            next((i for i in boundaries if i > start), len(chunks)),
            next((s for s in starts if s > first_item), len(chunks)),
        )
        wording = "\n".join(chunk.text for chunk in sources)
        terms = defined_terms(wording)
        quoted = (
            bool(following)
            and _is_lead_in(sources[-1])
            and _opens_with_quote(item_sources[following[0]])
        )
        for k in following:
            if not ordered[k][0] < end:
                break
            if terms and not uses_term(terms, item_sources[k]):
                continue
            if quoted and not _opens_with_quote(item_sources[k]):
                continue
            carried.setdefault(k, []).append(wording)
    return [
        (
            position,
            anchors,
            _with_paragraphs(
                _with_paragraphs(item, joined.get(k, []), first=False),
                carried.get(k, []),
                first=True,
            ),
        )
        for k, (position, anchors, item) in enumerate(ordered)
    ]


def _ordered_items(
    chunks: tuple[DocxChunk, ...],
    accepted: tuple[tuple[NativeExamItem, tuple[str, ...]], ...],
    review_reasons: dict[str, str],
    instructions: tuple[ProducedMetadata, ...],
) -> tuple[NativeExamItem, ...]:
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
    ordered = _with_section_instructions(chunks, ordered, instructions)
    return tuple(
        item.model_copy(update={"item_id": f"item_{i:03d}", "sequence": i})
        for i, (_, _, item) in enumerate(ordered, start=1)
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
        empty = "Dokumentet saknar läsbart innehåll."
        chunks = (DocxChunk("empty", "paragraph", empty, empty),)
        review_reasons = {"empty": "Dokumentet saknar läsbart innehåll."}
    items = _ordered_items(chunks, accepted, review_reasons, instructions)
    notes = [chunk.text for chunk in chunks if chunk.anchor in key_anchors]
    notes.extend(dict.fromkeys(reason for item in items for reason in item.review.reasons))
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
            extractor_version="docx_ai_build_v2",
        ),
    )
    return DocxBuildResult(document, tuple(notes), input_tokens, output_tokens, events)
