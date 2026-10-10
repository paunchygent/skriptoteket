"""Pure source-bound contracts for batched DOCX item construction."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredOutputSpec,
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


class SourceText(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    text: str = Field(min_length=1)
    source_anchors: tuple[str, ...] = Field(min_length=1)


class SourceEvidence(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    anchor: str
    text: str = Field(min_length=1)


class KeyEvidence(SourceEvidence):
    target_id: str
    value: str = Field(min_length=1)


class DocxBuildEntry(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    item: NativeExamItem
    source_anchors: tuple[str, ...] = Field(min_length=1)
    question_label: str = Field(min_length=1)
    points_evidence: SourceEvidence | None
    key_evidence: tuple[KeyEvidence, ...]


class DocxBuildEnvelope(BaseModel):
    """Provider shape; entries are validated separately at admission."""

    model_config = ConfigDict(frozen=True, extra="forbid")
    title: SourceText | None
    instructions: tuple[SourceText, ...]
    items: tuple[DocxBuildEntry, ...]


@dataclass(frozen=True)
class DocxBuildResult:
    document: NativeExamDocument
    notes: tuple[str, ...]
    input_tokens: int | None = None
    output_tokens: int | None = None


def normalize_text(text: str) -> str:
    return " ".join(text.split())


def _strict_schema(value: Any) -> Any:
    if isinstance(value, list):
        return [_strict_schema(entry) for entry in value]
    if not isinstance(value, dict):
        return value
    result = {
        ("anyOf" if key == "oneOf" else key): _strict_schema(entry)
        for key, entry in value.items()
        if key not in {"default", "discriminator"}
    }
    if result.get("type") == "object":
        result["additionalProperties"] = False
        result["required"] = list(result.get("properties", {}))
    return result


def docx_build_output_spec() -> StructuredOutputSpec:
    return StructuredOutputSpec(
        schema_name="docx_exam_build",
        schema_version="docx_exam_build_v1",
        json_schema=_strict_schema(DocxBuildEnvelope.model_json_schema()),
    )


def _required_shape(value: Any, schema: dict[str, Any], definitions: dict[str, Any]) -> None:
    """Enforce API-required fields, including native fields with Python defaults."""
    if "$ref" in schema:
        _required_shape(value, definitions[schema["$ref"].rsplit("/", 1)[1]], definitions)
        return
    if "anyOf" in schema:
        for branch in schema["anyOf"]:
            try:
                _required_shape(value, branch, definitions)
                return
            except ValueError:
                pass
        raise ValueError("Svaret följer inte JSON-schemat.")
    kind = schema.get("type")
    valid_type = {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "null": value is None,
        "integer": type(value) is int,
        "number": type(value) in {int, float},
        "boolean": type(value) is bool,
    }
    if kind in valid_type and not valid_type[kind]:
        raise ValueError("Svaret följer inte JSON-schemat.")
    if "const" in schema and value != schema["const"]:
        raise ValueError("Svaret följer inte JSON-schemat.")
    if "enum" in schema and value not in schema["enum"]:
        raise ValueError("Svaret följer inte JSON-schemat.")
    if kind == "object":
        properties = schema["properties"]
        if set(value) != set(properties):
            raise ValueError("Svaret saknar fält eller innehåller okända fält.")
        for key, child in properties.items():
            _required_shape(value[key], child, definitions)
    elif kind == "array":
        for child in value:
            _required_shape(child, schema["items"], definitions)


def parse_build_entry(value: JsonValue) -> DocxBuildEntry:
    schema = docx_build_output_spec().json_schema
    definitions = schema["$defs"]
    assert isinstance(definitions, dict)
    _required_shape(value, {"$ref": "#/$defs/DocxBuildEntry"}, definitions)
    return DocxBuildEntry.model_validate_json(json.dumps(value), strict=True)


_POINTS = re.compile(r"(?<![\w.,])(?P<points>\d+(?:[.,]\d+)?)\s*(?:poäng|points?|p)\b", re.I)
_KEY_HEADING = re.compile(
    r"^(?:facit|answer\s+key|answers|svar|lösningsförslag)\s*(?::|[-–].*)?$", re.I
)
_INLINE_KEY = re.compile(r"^\s*(?:correct\s+answers?|rätt\s+svar|facit|svar)\s*:\s*(.+)$", re.I)


def answer_key_chunks(chunks: tuple[DocxChunk, ...]) -> tuple[DocxChunk, ...]:
    """Identify general answer-key sections, without interpreting question wording."""
    result: list[DocxChunk] = []
    in_key = False
    for chunk in chunks:
        first_line = chunk.text.splitlines()[0].strip()
        if _KEY_HEADING.fullmatch(first_line):
            in_key = True
        elif chunk.kind == "heading":
            in_key = False
        if in_key or _INLINE_KEY.match(first_line):
            result.append(chunk)
    return tuple(result)


def _bound_text(text: str, anchors: tuple[str, ...], chunks: dict[str, DocxChunk]) -> None:
    if not anchors or len(set(anchors)) != len(anchors) or any(a not in chunks for a in anchors):
        raise ValueError("Källankaret saknas eller är ogiltigt.")
    normalized = normalize_text(text)
    if not normalized or not any(normalized in normalize_text(chunks[a].text) for a in anchors):
        raise ValueError("Texten kan inte beläggas i den angivna källan.")


def validate_source_text(value: SourceText, chunks: tuple[DocxChunk, ...]) -> None:
    _bound_text(value.text, value.source_anchors, {c.anchor: c for c in chunks})


def _label_prefix(label: str) -> re.Pattern[str]:
    if not re.fullmatch(r"(?:\d+|[A-Za-z])", label):
        raise ValueError("Frågans nummer eller bokstav saknas.")
    return re.compile(
        rf"^\s*(?:(?:question|fråga)\s+)?{re.escape(label)}(?:[.):\-]|\s)\s*(.*)$", re.I
    )


def _key_answer(
    evidence: KeyEvidence,
    entry: DocxBuildEntry,
    chunks: tuple[DocxChunk, ...],
    key_chunks: dict[str, DocxChunk],
) -> str:
    _bound_text(evidence.text, (evidence.anchor,), key_chunks)
    # The quote must be a complete numbered key line, not a convenient substring.
    for line in key_chunks[evidence.anchor].text.splitlines():
        if normalize_text(line) == normalize_text(evidence.text):
            inline = _INLINE_KEY.match(line)
            if inline:
                positions = {c.anchor: i for i, c in enumerate(chunks)}
                question_positions = [
                    positions[a] for a in entry.source_anchors if a not in key_chunks
                ]
                if question_positions and positions[evidence.anchor] == max(question_positions) + 1:
                    return inline[1].strip()
                raise ValueError("Det infogade facitbelägget hör inte till den angränsande frågan.")
            match = _label_prefix(entry.question_label).match(line)
            if match:
                return match.group(1).strip()
    raise ValueError("Facitbelägget är inte en facitrad knuten till frågans nummer.")


def _answer_values(answer: str) -> tuple[str, ...]:
    # Explanations after a dash do not constitute additional keyed answers.
    answer = re.split(r"\s+[—–-]\s+", answer, maxsplit=1)[0]
    return tuple(
        normalize_text(v).strip(" .)") for v in re.split(r"[,;/]|\s+(?:and|och)\s+", answer)
    )


def _require_consumed_source(
    texts: list[str], anchors: tuple[str, ...], source: dict[str, DocxChunk]
) -> None:
    """A claimed question chunk cannot conceal omitted wording or choices."""
    for anchor in anchors:
        remaining = source[anchor].text
        remaining = re.sub(r"^\s*(?:[A-Za-z]|\d+)[.):]\s*", "", remaining, flags=re.M)
        remaining = _POINTS.sub("", remaining)
        remaining = re.sub(r"_{2,}", "", remaining)
        remaining = normalize_text(remaining)
        for text in sorted((normalize_text(t) for t in texts), key=len, reverse=True):
            # Strip source labels/point markers from copied body text in the same way.
            visible = _POINTS.sub("", re.sub(r"^\s*(?:[A-Za-z]|\d+)[.):]\s*", "", text))
            visible = normalize_text(visible)
            if visible:
                remaining = remaining.replace(visible, "")
        if re.search(r"\w", remaining):
            raise ValueError("Frågan lämnar källtext eller svarsalternativ obehandlade.")


def _choice_labels(text: str, anchors: tuple[str, ...], source: dict[str, DocxChunk]) -> set[str]:
    labels: set[str] = set()
    for anchor in anchors:
        for line in source[anchor].text.splitlines():
            match = re.match(r"^\s*([A-Za-z]|\d+)[.)]\s*(.+)$", line)
            if match and normalize_text(match[2]) == normalize_text(text):
                labels.add(match[1].casefold())
    return labels


def _choice_matches(answer: str, text: str, labels: set[str]) -> bool:
    if normalize_text(text) == normalize_text(answer):
        return True
    for value in _answer_values(answer):
        if normalize_text(text) == value:
            return True
        match = re.fullmatch(r"([A-Za-z]|\d+)(?:[.)]\s*(.+))?", value)
        if (
            match
            and match[1].casefold() in labels
            and (not match[2] or normalize_text(match[2]) == normalize_text(text))
        ):
            return True
    return False


def validate_build_entry(entry: DocxBuildEntry, chunks: tuple[DocxChunk, ...]) -> NativeExamItem:
    """Admit one native item only with source-bound student text, points and key."""
    source = {c.anchor: c for c in chunks}
    keys = {c.anchor: c for c in answer_key_chunks(chunks)}
    _bound_text(entry.question_label, entry.source_anchors, source)
    anchors = tuple(a for a in entry.source_anchors if a not in keys)
    item = entry.item
    labelled_heading = any(
        source[a].kind == "heading"
        and normalize_text(source[a].text) == normalize_text(entry.question_label)
        for a in anchors
    )
    numbered = False
    if re.fullmatch(r"(?:\d+|[A-Za-z])", entry.question_label):
        prefix = _label_prefix(entry.question_label)
        numbered = any(prefix.match(line) for a in anchors for line in source[a].text.splitlines())
    if not labelled_heading and not numbered:
        raise ValueError("Frågans nummer kan inte beläggas i frågekällan.")
    texts = [item.title] if item.title is not None else []
    texts.extend(choice.text for choice in item.choices)
    texts.extend(gap.hint for gap in item.gaps if gap.hint is not None)
    for paragraph in item.body:
        for segment in paragraph.segments:
            if isinstance(segment, NativeTextSegment):
                texts.append(segment.text)
            elif segment.kind == "asset":
                raise ValueError("Bildreferensen kan inte beläggas i textkällan.")
        if any(s.kind == "gap" for s in paragraph.segments):
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

    source_points = [m for a in anchors for m in _POINTS.finditer(source[a].text)]
    if item.points is None:
        if source_points or entry.points_evidence is not None:
            raise ValueError("Källans poäng saknas i frågan.")
    else:
        evidence = entry.points_evidence
        if evidence is None or evidence.anchor not in anchors:
            raise ValueError("Poängen saknar källbelägg.")
        _bound_text(evidence.text, (evidence.anchor,), source)
        found = _POINTS.fullmatch(evidence.text.strip())
        if found is None or float(found["points"].replace(",", ".")) != item.points:
            raise ValueError("Poängen stämmer inte med källan.")
        if len(source_points) != 1:
            raise ValueError("Frågans poäng kan inte knytas entydigt till källan.")

    expected: set[tuple[str, str]] = set()
    for choice_id in item.answer_key.correct_choice_ids:
        choice = next(c for c in item.choices if c.choice_id == choice_id)
        expected.add((choice_id, choice.text))
    expected.update((gap.gap_id, value) for gap in item.gaps for value in gap.accepted_values)
    if item.kind is not NativeExamItemKind.FREE_TEXT and not expected:
        raise ValueError("Frågans facit saknas.")
    if len(item.answer_key.correct_choice_ids) != len(set(item.answer_key.correct_choice_ids)):
        raise ValueError("Facit innehåller upprepade alternativ.")
    if {(e.target_id, e.value) for e in entry.key_evidence} != expected:
        raise ValueError("Facitbeläggen stämmer inte med frågans svar.")
    if len(item.gaps) > 1:
        raise ValueError("Facit kan inte knytas entydigt till flera luckor i samma fråga.")
    source_correct: set[str] = set()
    for evidence in entry.key_evidence:
        answer = _key_answer(evidence, entry, chunks, keys)
        values = _answer_values(answer)
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
        elif (
            normalize_text(evidence.value) == normalize_text(answer)
            or normalize_text(evidence.value) in values
        ):
            continue
        else:
            raise ValueError("Facitvärdet är inte det svar som anges på facitraden.")
    if item.choices and source_correct != set(item.answer_key.correct_choice_ids):
        raise ValueError("Frågans rätta alternativ stämmer inte med hela facitraden.")
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
    items = tuple(
        item.model_copy(update={"item_id": f"item_{i:03d}", "sequence": i})
        for i, (_, item) in enumerate(ordered, start=1)
    )
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
