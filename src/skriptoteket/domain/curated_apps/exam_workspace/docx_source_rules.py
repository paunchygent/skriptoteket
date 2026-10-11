"""Source-structure invariants a produced item, key list or title must satisfy.

Each check reads only the source chunks. A violation is an English message for the
model's next round; it names source features and counts, never exam wording.
"""

import re
from collections.abc import Iterable

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
    ProducedItem,
    ProducedMetadata,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk

# Where the student writes: an underscore run, a dotted line, or empty brackets.
_BLANK_MARKER = re.compile(r"_{3,}|\.{4,}|…{2,}|\[\s*\]|\(\s*\)")
_ITALIC = re.compile(r"<i>(.*?)</i>", re.DOTALL)
# A mark that splits text into units: units joined with "+", or a label after each unit.
_PLUS_JOIN = re.compile(r"\S\s*\+\s*\S")
_UNIT_LABEL = re.compile(r"\(\s*[^()\s][^()]{0,11}\)")
_TITLE_SEPARATORS = " \t\n—–-:,|"


def _normalized(text: str) -> str:
    return " ".join(text.split())


def _segments_units(mark: str) -> bool:
    return bool(_PLUS_JOIN.search(mark)) or len(_UNIT_LABEL.findall(mark)) >= 2


def item_rule_violation(item: ProducedItem, sources: Iterable[DocxChunk]) -> str | None:
    """Rules 1 and 2: gaps come from answer slots; segmentation tasks are free text."""
    if item.outcome == "review":
        return None
    texts = [chunk.marked_text for chunk in sources]
    blanks = sum(len(_BLANK_MARKER.findall(text)) for text in texts)
    marks = [mark for text in texts for mark in _ITALIC.findall(text)]
    gaps = sum(1 for p in item.body for s in p.segments if s.kind == "gap")
    if gaps and any(_segments_units(mark) for mark in marks):
        return (
            "its facit splits the text into units (joined with + or with a label after each "
            "unit), so the student decides where units start and end: make it free_text "
            "with no gaps and keep the facit out of the body"
        )
    if blanks and not gaps and not item.choices:
        return (
            f"its source shows {blanks} blank marker(s) (an underscore run, dotted line or "
            "empty brackets) and has no options: each blank the student fills in is a gap"
        )
    if gaps > blanks + len(marks):
        return (
            f"it has {gaps} gaps but its source shows {blanks} blank marker(s) and "
            f"{len(marks)} inline answer mark(s): the facit never creates a gap of its own"
        )
    return None


def opening_heading(chunks: tuple[DocxChunk, ...]) -> DocxChunk | None:
    """The exam's heading: the document's first chunk when it is a heading."""
    if chunks and chunks[0].kind == "heading":
        return chunks[0]
    return None


OPENING_HEADING_IS_TITLE = (
    "is the document's opening heading, which is the exam title copied verbatim; a chunk is "
    "facit by its position (an answer line, or text under a facit heading), never because "
    "its wording mentions answers"
)


def title_rule_violation(
    title: ProducedMetadata, sources: Iterable[DocxChunk], heading: DocxChunk | None
) -> str | None:
    """Rule 5: the title copies the opening heading's text verbatim."""
    sources = tuple(sources)
    if heading is not None and heading.anchor not in title.source_anchors:
        return f"title must be the opening heading {heading.anchor}, copied verbatim"
    remainder = _normalized(title.text)
    for chunk in sources:
        source_text = _normalized(chunk.text)
        if source_text not in remainder:
            return f"title text must copy {chunk.anchor} verbatim"
        remainder = remainder.replace(source_text, " ", 1)
    if remainder.strip(_TITLE_SEPARATORS):
        return "title text must hold only its source chunks' wording, copied verbatim"
    return None


# "short = term" in an instruction: a short form of up to six characters, then "=".
_SHORT_FORM = re.compile(r"(?<![^\s(])([^\s=(),;:]{1,6})\s*=\s*")


def definition_context(
    chunks: tuple[DocxChunk, ...], anchors: tuple[str, ...]
) -> tuple[DocxChunk, ...]:
    """The item's own chunks plus the lines above it back to the nearest heading before it."""
    positions = {chunk.anchor: index for index, chunk in enumerate(chunks)}
    context = [chunks[positions[anchor]] for anchor in anchors]
    index = min(positions[anchor] for anchor in anchors) - 1
    while index >= 0 and chunks[index].kind != "heading":
        context.append(chunks[index])
        index -= 1
    return tuple(context)


def _defines(rest: str, value: str) -> bool:
    folded, wanted = rest.casefold(), value.casefold().strip()
    if not wanted or not folded.startswith(wanted):
        return False
    return len(folded) == len(wanted) or not folded[len(wanted)].isalnum()


def _definitions(context: Iterable[DocxChunk]) -> list[tuple[str, str]]:
    """Each "short = term" as (short form, the text from its term to the next definition)."""
    definitions: list[tuple[str, str]] = []
    for chunk in context:
        matches = list(_SHORT_FORM.finditer(chunk.text))
        if not matches:
            continue
        ends = [following.start() for following in matches[1:]] + [len(chunk.text)]
        definitions.extend(
            (match.group(1), chunk.text[match.end() : end])
            for match, end in zip(matches, ends, strict=True)
        )
    return definitions


def with_defined_short_forms(item: ProducedItem, context: Iterable[DocxChunk]) -> ProducedItem:
    """Rule 3: a gap accepts the facit's own form plus the short form the instructions define.

    A facit term also accepts its short form. When the inline facit marks write the short
    form, the term is neither the facit's form nor the form students are told to use, so a
    term the model added is dropped.
    """
    context = tuple(context)
    definitions = _definitions(context)
    if not definitions:
        return item
    marks = {
        mark.casefold().strip()
        for chunk in context
        if chunk.anchor in item.source_anchors
        for mark in _ITALIC.findall(chunk.marked_text)
    }

    def added_term(value: str) -> bool:
        return value.casefold().strip() not in marks and any(
            short.casefold() in marks and _defines(rest, value) for short, rest in definitions
        )

    body = []
    for paragraph in item.body:
        segments = []
        for segment in paragraph.segments:
            facit = tuple(value for value in segment.accepted_values if not added_term(value))
            values = list(facit)
            for short, rest in definitions:
                known = {value.casefold() for value in values}
                if short.casefold() not in known and any(_defines(rest, v) for v in facit):
                    values.append(short)
            segments.append(segment.model_copy(update={"accepted_values": tuple(values)}))
        body.append(paragraph.model_copy(update={"segments": tuple(segments)}))
    return item.model_copy(update={"body": tuple(body)})
