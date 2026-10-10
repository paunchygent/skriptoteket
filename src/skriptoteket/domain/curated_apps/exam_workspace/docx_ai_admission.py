"""Admit native items with question-bound wording, points and facit."""

import re

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import DocxBuildEntry
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_source import (
    _POINTS,
    _answer_values,
    _bound_text,
    _choice_labels,
    _choice_matches,
    _key_answer,
    _require_consumed_source,
    answer_key_chunks,
    normalize_text,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeAnswerKeyOrigin,
    NativeExamItem,
    NativeExamItemKind,
    NativeItemReview,
    NativeItemReviewState,
    NativeParseOrigin,
    NativeTextSegment,
)


def _prompt_texts(item: NativeExamItem) -> list[str]:
    texts = [item.title] if item.title is not None else []
    texts.extend(
        segment.text
        for paragraph in item.body
        for segment in paragraph.segments
        if isinstance(segment, NativeTextSegment)
    )
    return texts


def _require_question_identity(
    entry: DocxBuildEntry, anchors: tuple[str, ...], source: dict[str, DocxChunk]
) -> None:
    """Labels must belong to the heading or copied prompt, excluding options."""
    prompts = [entry.item.title] if entry.item.title else []
    if entry.item.body:
        first_line = "".join(
            segment.text if isinstance(segment, NativeTextSegment) else "[___]"
            for segment in entry.item.body[0].segments
        ).splitlines()[0]
        prompts.append(first_line)
    if not re.fullmatch(r"(?:\d+|[A-Za-z])", entry.question_label):
        if any(
            source[a].kind == "heading"
            and normalize_text(source[a].text) == normalize_text(entry.question_label)
            and any(normalize_text(source[a].text) == normalize_text(text) for text in prompts)
            for a in anchors
        ):
            return
    elif _question_labels(prompts, entry.item, anchors, source) == {
        entry.question_label.casefold()
    }:
        return
    raise ValueError("Frågans nummer kan inte beläggas i frågans rubrik eller text.")


def _unlabelled_prompt(text: str) -> str:
    text = re.sub(r"^\s*(?:(?:question|fråga)\s+)?(?:\d+|[A-Za-z])[.):\-]\s*", "", text)
    return normalize_text(_POINTS.sub("", text)).strip(" ()")


def _question_labels(
    prompts: list[str], item: NativeExamItem, anchors: tuple[str, ...], source: dict[str, DocxChunk]
) -> set[str]:
    prompt_texts = {_unlabelled_prompt(text) for text in prompts}
    options = {_unlabelled_prompt(choice.text) for choice in item.choices}
    labels: set[str] = set()
    for anchor in anchors:
        # A question starts at its heading or prompt, never a later option line.
        line = source[anchor].text.splitlines()[0]
        match = re.match(
            r"^\s*(?:(?:question|fråga)\s+)?(\d+|[A-Za-z])(?:[.):\-]|\s)\s*(.+)$", line, re.I
        )
        text = _unlabelled_prompt(line)
        if match and text in prompt_texts and text not in options:
            labels.add(match[1].casefold())
    return labels


def _require_student_text(
    item: NativeExamItem, anchors: tuple[str, ...], source: dict[str, DocxChunk]
) -> None:
    texts = _prompt_texts(item)
    texts.extend(choice.text for choice in item.choices)
    texts.extend(gap.hint for gap in item.gaps if gap.hint is not None)
    for paragraph in item.body:
        if any(segment.kind == "asset" for segment in paragraph.segments):
            raise ValueError("Bildreferensen kan inte beläggas i textkällan.")
        if any(segment.kind == "gap" for segment in paragraph.segments):
            rendered = "".join(
                s.text if isinstance(s, NativeTextSegment) else "[___]" for s in paragraph.segments
            )
            if not any(
                normalize_text(rendered)
                in normalize_text(re.sub(r"_{2,}", "[___]", source[a].text))
                for a in anchors
            ):
                raise ValueError("Luckans placering stämmer inte med källans tomrum.")
    for text in texts:
        _bound_text(text, anchors, source)
    _require_consumed_source(texts, anchors, source)


def _require_points(
    entry: DocxBuildEntry, anchors: tuple[str, ...], source: dict[str, DocxChunk]
) -> None:
    annotations = [(a, m) for a in anchors for m in _POINTS.finditer(source[a].text)]
    evidence = entry.points_evidence
    if entry.item.points is None:
        if annotations or evidence is not None:
            raise ValueError("Källans poäng saknas i frågan.")
        return
    if evidence is None or evidence.anchor not in anchors:
        raise ValueError("Poängen saknar källbelägg.")
    if len(annotations) != 1:
        raise ValueError("Frågans poäng kan inte knytas entydigt till källan.")
    anchor, annotation = annotations[0]
    if (
        evidence.anchor != anchor
        or normalize_text(evidence.text) != normalize_text(annotation[0])
        or float(annotation["points"].replace(",", ".")) != entry.item.points
    ):
        raise ValueError("Poängen stämmer inte med källan.")


def _require_key_shape(entry: DocxBuildEntry) -> None:
    item = entry.item
    expected = {
        (choice_id, next(c.text for c in item.choices if c.choice_id == choice_id))
        for choice_id in item.answer_key.correct_choice_ids
    }
    expected.update((gap.gap_id, value) for gap in item.gaps for value in gap.accepted_values)
    if item.kind is not NativeExamItemKind.FREE_TEXT and not expected:
        raise ValueError("Frågans facit saknas.")
    if len(item.answer_key.correct_choice_ids) != len(set(item.answer_key.correct_choice_ids)):
        raise ValueError("Facit innehåller upprepade alternativ.")
    if {(e.target_id, e.value) for e in entry.key_evidence} != expected:
        raise ValueError("Facitbeläggen stämmer inte med frågans svar.")
    if len(item.gaps) > 1:
        raise ValueError("Facit kan inte knytas entydigt till flera luckor i samma fråga.")


def _require_source_key(
    entry: DocxBuildEntry,
    chunks: tuple[DocxChunk, ...],
    keys: dict[str, DocxChunk],
    anchors: tuple[str, ...],
    source: dict[str, DocxChunk],
) -> None:
    _require_key_shape(entry)
    item = entry.item
    source_correct: set[str] = set()
    for evidence in entry.key_evidence:
        answer = _key_answer(evidence, entry, chunks, keys)
        if item.choices:
            matches = {
                choice.choice_id
                for choice in item.choices
                if _choice_matches(
                    answer, choice.text, _choice_labels(choice.text, anchors, source)
                )
            }
            if evidence.target_id not in matches:
                raise ValueError("Facitvärdet är inte det svar som anges på facitraden.")
            source_correct.update(matches)
        elif not (
            normalize_text(evidence.value) == normalize_text(answer)
            or normalize_text(evidence.value) in _answer_values(answer)
        ):
            raise ValueError("Facitvärdet är inte det svar som anges på facitraden.")
    if item.choices and source_correct != set(item.answer_key.correct_choice_ids):
        raise ValueError("Frågans rätta alternativ stämmer inte med hela facitraden.")


def validate_build_entry(entry: DocxBuildEntry, chunks: tuple[DocxChunk, ...]) -> NativeExamItem:
    """Admit one item only with source-bound student text, points and key."""
    source = {chunk.anchor: chunk for chunk in chunks}
    keys = {chunk.anchor: chunk for chunk in answer_key_chunks(chunks)}
    _bound_text(entry.question_label, entry.source_anchors, source)
    anchors = tuple(anchor for anchor in entry.source_anchors if anchor not in keys)
    _require_student_text(entry.item, anchors, source)
    _require_question_identity(entry, anchors, source)
    _require_points(entry, anchors, source)
    _require_source_key(entry, chunks, keys, anchors, source)
    item = entry.item
    return item.model_copy(
        update={
            "source_anchor": anchors[0],
            "answer_key": item.answer_key.model_copy(
                update={
                    "origin": (
                        NativeAnswerKeyOrigin.NOT_APPLICABLE
                        if item.kind is NativeExamItemKind.FREE_TEXT
                        else NativeAnswerKeyOrigin.SOURCE_PROVIDED
                    )
                }
            ),
            "review": NativeItemReview(
                state=NativeItemReviewState.REVIEW_COMPLETE,
                parse_origin=NativeParseOrigin.LLM_PARSED,
            ),
        }
    )
