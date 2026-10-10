"""Source text, question labels and facit evidence binding rules."""

import re

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
    DocxBuildEntry,
    KeyEvidence,
    SourceText,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk


def normalize_text(text: str) -> str:
    return " ".join(text.split())


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
