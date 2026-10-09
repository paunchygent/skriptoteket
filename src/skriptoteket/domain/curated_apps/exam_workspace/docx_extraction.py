"""Deterministic DOCX exam extraction rules (ST-SKRIPT-39-04, EPIC-39 E4).

Pure domain: the input is a neutral block stream (produced by the
python-docx infrastructure adapter), the output is a native exam document
with per-item confidence and review state. Rules are layout/regex policy
only; anything the rules cannot resolve stays visible in item bodies and
is routed to teacher review, never dropped.
"""

from __future__ import annotations

import re
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeAnswerKey,
    NativeAnswerKeyOrigin,
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
    NativeTextSegment,
)

DOCX_EXTRACTOR_VERSION = "docx_extractor_v1"

_QUESTION_HEADING_RE = re.compile(r"^(?:Fråga|Uppgift|Question)\s+\d+\b", re.IGNORECASE)
_SUBLINE_RE = re.compile(r"^([a-h])\)\s*(.+)$")
_POINTS_LINE_RE = re.compile(r"^Poäng:\s*(\d+(?:[.,]\d+)?)\s*(?:poäng|p)\s*$", re.IGNORECASE)
_TITLE_POINTS_RE = re.compile(r"\((\d+(?:[.,]\d+)?)\s*p(?:oäng)?\)", re.IGNORECASE)

# Ordered longest-first so compound labels win over their prefixes.
_ANSWER_LABELS = (
    "Bisats 1 satsdel",
    "Bisats 2 satsdel",
    "Markerad del",
    "Rätt svar",
    "Bisats 1",
    "Bisats 2",
    "Frastyp",
    "Huvudord",
    "Satsdel",
    "Analys",
    "Bisats",
    "Facit",
    "Svar",
    "Typ",
)
_ANSWER_LABEL_RE = re.compile(
    r"(?:(?<=\s)|^)(" + "|".join(re.escape(label) for label in _ANSWER_LABELS) + r")\s*:\s*"
)

_LONG_ANSWER_THRESHOLD = 60


class DocxBlockKind(StrEnum):
    TITLE = "title"
    SECTION = "section"
    HEADING = "heading"
    BODY = "body"
    LIST = "list"


class DocxSourceBlock(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: DocxBlockKind
    text: str = Field(min_length=1)
    index: int = Field(ge=0)


class DocxExtractionResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    document: NativeExamDocument
    notes: tuple[str, ...] = ()


class _SubLine(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    letter: str
    raw: str
    stem: str
    label: str | None
    answer: str | None
    label_count: int


def _split_answer_label(text: str) -> tuple[str, str | None, str | None, int]:
    matches = list(_ANSWER_LABEL_RE.finditer(text))
    if not matches:
        return text.strip(), None, None, 0
    first = matches[0]
    stem = text[: first.start()].strip()
    answer = text[first.end() :].strip()
    return stem, first.group(1), answer or None, len(matches)


class _ItemDraft:
    def __init__(self, *, heading: str, context: list[str], anchor: int) -> None:
        self.heading = heading
        self.context = context
        self.anchor = anchor
        self.paragraph_texts: list[str] = []
        self.sublines: list[_SubLine] = []
        self.points: float | None = None
        self.points_seen = False

    def title_points(self) -> float | None:
        match = _TITLE_POINTS_RE.search(self.heading)
        if match is None:
            return None
        return float(match.group(1).replace(",", "."))


def _normalize_points(points: float | None) -> int | float | None:
    if points is None:
        return None
    if points <= 0:
        return None
    return int(points) if float(points).is_integer() else points


def _build_item(draft: _ItemDraft, *, item_number: int, sequence: int) -> NativeExamItem:
    item_id = f"item_{item_number:03d}"
    points = _normalize_points(draft.points if draft.points is not None else draft.title_points())

    reasons: list[str] = []
    confidence = 0.9
    keyed = [line for line in draft.sublines if line.answer is not None]
    unkeyed = [line for line in draft.sublines if line.answer is None]

    context_paragraphs = tuple(
        NativeParagraph(segments=(NativeTextSegment(text=text),))
        for text in (*draft.context, *draft.paragraph_texts)
        if text
    )

    if draft.sublines and keyed and not unkeyed:
        gaps: list[NativeGap] = []
        gap_paragraphs: list[NativeParagraph] = []
        for position, line in enumerate(draft.sublines, start=1):
            gap_id = f"gap_{position:03d}"
            assert line.answer is not None and line.label is not None
            gaps.append(NativeGap(gap_id=gap_id, accepted_values=(line.answer,)))
            visible = f"{line.letter}) {line.stem} {line.label}: ".replace("  ", " ")
            gap_paragraphs.append(
                NativeParagraph(
                    segments=(
                        NativeTextSegment(text=visible),
                        NativeGapSegment(gap_id=gap_id),
                    )
                )
            )
            if line.label_count > 1:
                confidence = min(confidence, 0.55)
                if "multiple_answer_labels_detected" not in reasons:
                    reasons.append("multiple_answer_labels_detected")
            if len(line.answer) > _LONG_ANSWER_THRESHOLD:
                confidence = min(confidence, 0.7)
                if "long_answer_key" not in reasons:
                    reasons.append("long_answer_key")
        kind = NativeExamItemKind.GAP_FILL
        body = (*context_paragraphs, *gap_paragraphs)
        answer_key = NativeAnswerKey(origin=NativeAnswerKeyOrigin.SOURCE_PROVIDED)
        gaps_tuple = tuple(gaps)
    else:
        if keyed and unkeyed:
            confidence = min(confidence, 0.5)
            reasons.append("partial_answer_keys_detected")
        elif not draft.sublines:
            confidence = min(confidence, 0.85)
        else:
            confidence = min(confidence, 0.75)
            reasons.append("sublines_without_answer_keys")
        kind = NativeExamItemKind.FREE_TEXT
        subline_paragraphs = tuple(
            NativeParagraph(segments=(NativeTextSegment(text=f"{line.letter}) {line.raw}"),))
            for line in draft.sublines
        )
        body = (*context_paragraphs, *subline_paragraphs)
        answer_key = NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE)
        gaps_tuple = ()

    if not body:
        body = (NativeParagraph(segments=(NativeTextSegment(text=draft.heading),)),)

    if points is None:
        confidence -= 0.1
        reasons.append("missing_points")

    state = (
        NativeItemReviewState.REVIEW_COMPLETE
        if confidence >= 0.8 and points is not None
        else NativeItemReviewState.REVIEW_REQUIRED
    )
    return NativeExamItem(
        item_id=item_id,
        sequence=sequence,
        kind=kind,
        title=draft.heading,
        body=body,
        points=points,
        gaps=gaps_tuple,
        answer_key=answer_key,
        review=NativeItemReview(
            state=state,
            parse_origin=NativeParseOrigin.DETERMINISTIC,
            confidence=round(max(confidence, 0.0), 2),
            reasons=tuple(reasons),
        ),
        source_anchor=f"block:{draft.anchor}",
    )


def extract_native_exam_from_docx_blocks(
    *,
    blocks: tuple[DocxSourceBlock, ...],
    document_id: UUID,
    source_filename: str,
    source_sha256: str,
    notes: tuple[str, ...] = (),
) -> DocxExtractionResult:
    title: str | None = None
    instructions: list[str] = []
    pending_context: list[str] = []
    drafts: list[_ItemDraft] = []
    current: _ItemDraft | None = None
    extraction_notes = list(notes)

    for block in blocks:
        if block.kind is DocxBlockKind.TITLE and title is None and current is None:
            title = block.text
            continue
        is_question_heading = (
            block.kind is DocxBlockKind.HEADING
            and _QUESTION_HEADING_RE.match(block.text) is not None
        )
        if is_question_heading:
            current = _ItemDraft(
                heading=block.text,
                context=pending_context,
                anchor=block.index,
            )
            pending_context = []
            drafts.append(current)
            continue
        if block.kind in (DocxBlockKind.SECTION, DocxBlockKind.HEADING):
            pending_context.append(block.text)
            continue

        points_match = _POINTS_LINE_RE.match(block.text)
        if current is not None and points_match and not current.points_seen:
            current.points = float(points_match.group(1).replace(",", "."))
            current.points_seen = True
            continue

        if current is None:
            instructions.append(block.text)
            continue
        if current.points_seen:
            pending_context.append(block.text)
            continue

        subline_match = _SUBLINE_RE.match(block.text)
        if subline_match:
            letter, rest = subline_match.group(1), subline_match.group(2)
            stem, label, answer, label_count = _split_answer_label(rest)
            current.sublines.append(
                _SubLine(
                    letter=letter,
                    raw=rest,
                    stem=stem,
                    label=label,
                    answer=answer,
                    label_count=label_count,
                )
            )
            continue
        current.paragraph_texts.append(block.text)

    if pending_context:
        extraction_notes.append(f"trailing_content_not_assigned: {len(pending_context)} block(s)")

    items: tuple[NativeExamItem, ...]
    if drafts:
        items = tuple(
            _build_item(draft, item_number=index, sequence=index)
            for index, draft in enumerate(drafts, start=1)
        )
    else:
        fallback_lines = [block.text for block in blocks]
        items = (
            NativeExamItem(
                item_id="item_001",
                sequence=1,
                kind=NativeExamItemKind.FREE_TEXT,
                title=title or source_filename,
                body=tuple(
                    NativeParagraph(segments=(NativeTextSegment(text=line),))
                    for line in fallback_lines
                )
                or (NativeParagraph(segments=(NativeTextSegment(text=source_filename),)),),
                answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
                review=NativeItemReview(
                    state=NativeItemReviewState.REVIEW_REQUIRED,
                    parse_origin=NativeParseOrigin.DETERMINISTIC,
                    confidence=0.3,
                    reasons=("no_question_structure_detected",),
                ),
            ),
        )
        instructions = []

    document = NativeExamDocument(
        document_id=document_id,
        revision=1,
        title=title or source_filename,
        instructions=tuple(instructions),
        items=items,
        origin=NativeExamDocumentOrigin(
            kind="docx_import",
            source_filename=source_filename,
            source_sha256=source_sha256,
            extractor_version=DOCX_EXTRACTOR_VERSION,
        ),
    )
    return DocxExtractionResult(document=document, notes=tuple(extraction_notes))
