"""Source-structure invariants a produced item, key list or title must satisfy.

Each check reads only the source chunks. A violation is an English message for the
model's next round; it names source features and counts, never exam wording.
"""

import re
from collections.abc import Iterable

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
    ProducedItem,
    ProducedMetadata,
    ProducedSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamItemKind,
)
from skriptoteket.domain.errors import validation_error

# Where the student writes: an underscore run, a dotted line, or empty brackets.
_BLANK_MARKER = re.compile(r"_{3,}|\.{4,}|…{2,}|\[\s*\]|\(\s*\)")
_CHOICE_KINDS = (NativeExamItemKind.SINGLE_CHOICE, NativeExamItemKind.MULTIPLE_RESPONSE)
_ITALIC = re.compile(r"<i>(.*?)</i>", re.DOTALL)
# A mark that splits text into units: units joined with "+", or a label after each unit.
_PLUS_JOIN = re.compile(r"\S\s*\+\s*\S")
_UNIT_LABEL = re.compile(r"\(\s*[^()\s][^()]{0,11}\)")
_TITLE_SEPARATORS = " \t\n—–-:,|"
_ANSWER_KEY_PHRASES = ("answer key", "key", "facit", "med facit", "with answers", "svar")
_ANSWER_KEY_LABEL = "(?:" + "|".join(re.escape(phrase) for phrase in _ANSWER_KEY_PHRASES) + ")"
_ANSWER_KEY_PREFIX = re.compile(
    rf"\A\s*(?:{_ANSWER_KEY_LABEL}\s*[—–:,\-]|"
    rf"\(\s*{_ANSWER_KEY_LABEL}\s*\)(?:\s*[—–:,\-])?)\s*",
    re.IGNORECASE,
)
_ANSWER_KEY_SUFFIX = re.compile(
    rf"\s*(?:[—–:,\-]\s*{_ANSWER_KEY_LABEL}|"
    rf"(?:[—–:,\-]\s*)?\(\s*{_ANSWER_KEY_LABEL}\s*\))\s*\Z",
    re.IGNORECASE,
)
_FILENAME_ANSWER_KEY_LABEL = (
    "(?:"
    + "|".join(
        r"[\s_\-]+".join(re.escape(word) for word in phrase.split())
        for phrase in sorted(_ANSWER_KEY_PHRASES, key=len, reverse=True)
    )
    + ")"
)
_FILENAME_TITLE_DELIMITER = r"\s*[—–:,_\-]+\s*"
_FILENAME_ANSWER_KEY_PREFIX = re.compile(
    rf"\A\s*(?:{_FILENAME_ANSWER_KEY_LABEL}{_FILENAME_TITLE_DELIMITER}|"
    rf"\(\s*{_FILENAME_ANSWER_KEY_LABEL}\s*\)(?:{_FILENAME_TITLE_DELIMITER})?)\s*",
    re.IGNORECASE,
)
_FILENAME_ANSWER_KEY_SUFFIX = re.compile(
    rf"\s*(?:{_FILENAME_TITLE_DELIMITER}{_FILENAME_ANSWER_KEY_LABEL}|"
    rf"(?:{_FILENAME_TITLE_DELIMITER})?\(\s*{_FILENAME_ANSWER_KEY_LABEL}\s*\))\s*\Z",
    re.IGNORECASE,
)


def title_without_answer_key(text: str, *, filename: bool = False) -> str:
    """Remove delimited answer-key labels at either edge, preserving the title substring."""
    prefix_pattern = _FILENAME_ANSWER_KEY_PREFIX if filename else _ANSWER_KEY_PREFIX
    suffix_pattern = _FILENAME_ANSWER_KEY_SUFFIX if filename else _ANSWER_KEY_SUFFIX
    remainder = text
    while True:
        previous = remainder
        prefix = prefix_pattern.match(remainder)
        if prefix is not None:
            remainder = remainder[prefix.end() :]
        suffix = suffix_pattern.search(remainder)
        if suffix is not None:
            remainder = remainder[: suffix.start()]
        if not remainder.strip():
            raise validation_error("Removing answer-key wording would leave an empty title")
        if remainder == previous:
            return remainder


def _normalized(text: str) -> str:
    return " ".join(text.split())


def _segments_units(mark: str) -> bool:
    return bool(_PLUS_JOIN.search(mark)) or len(_UNIT_LABEL.findall(mark)) >= 2


def _restated_marks(chunk: DocxChunk) -> list[str]:
    """Inline facit phrases the line already prints as visible text, beside marks it does not.

    Only a phrase of two or more words counts, since a lone letter or word recurs by chance.
    """
    marks = [_normalized(mark).casefold() for mark in _ITALIC.findall(chunk.marked_text)]
    visible = _normalized(_ITALIC.sub(" ", chunk.marked_text)).casefold()
    printed = [
        m
        for m in marks
        if len(m.split()) >= 2 and re.search(rf"(?<!\w){re.escape(m)}(?!\w)", visible)
    ]
    return printed if len(printed) < len(marks) else []


def item_rule_violation(item: ProducedItem, sources: Iterable[DocxChunk]) -> str | None:
    """Rules 1 and 2: gaps come from answer slots; segmentation tasks are free text."""
    if item.outcome == "review":
        return None
    sources = tuple(sources)
    values = {
        _normalized(v).casefold() for p in item.body for s in p.segments for v in s.accepted_values
    }
    for chunk in sources:
        if values & set(_restated_marks(chunk)):
            return (
                f"a facit field on {chunk.anchor} repeats wording that line already shows the "
                "student, while its other facit fields are new: that field restates context, "
                "so it stays text with its value and is no gap"
            )
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
    if blanks and not gaps and not item.choices and not item.match_left:
        return (
            f"its source shows {blanks} blank marker(s) (an underscore run, dotted line or "
            "empty brackets) and has no options or match lists: each blank the student fills "
            "in is a gap"
        )
    if gaps > blanks + len(marks):
        return (
            f"it has {gaps} gaps but its source shows {blanks} blank marker(s) and "
            f"{len(marks)} inline answer mark(s): the facit never creates a gap of its own"
        )
    printed = sum(len(_BLANK_MARKER.findall(s.text or "")) for p in item.body for s in p.segments)
    if gaps and printed:
        return (
            f"its text still prints {printed} blank marker(s): the blank inside the sentence "
            "is the gap segment, and a separate line holding only a blank is no second gap"
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
    chunks: tuple[DocxChunk, ...],
    anchors: tuple[str, ...],
    instruction_anchors: Iterable[str] = (),
) -> tuple[DocxChunk, ...]:
    """The item's own chunks, the instructions printed among them, and the lines above it.

    An instruction the producer returned separately joins the item when it is printed between
    the item's first and last chunk. The lines above reach back to the nearest heading.
    """
    positions = {chunk.anchor: index for index, chunk in enumerate(chunks)}
    first = min(positions[anchor] for anchor in anchors)
    last = max(positions[anchor] for anchor in anchors)
    context = [chunks[positions[anchor]] for anchor in anchors]
    context.extend(
        chunks[positions[anchor]]
        for anchor in instruction_anchors
        if first < positions[anchor] < last and anchor not in anchors
    )
    index = first - 1
    while index >= 0 and chunks[index].kind != "heading":
        context.append(chunks[index])
        index -= 1
    return tuple(context)


def defines(rest: str, value: str) -> bool:
    """Whether a definition's term text starts with ``value`` as a whole word."""
    folded, wanted = rest.casefold(), value.casefold().strip()
    if not wanted or not folded.startswith(wanted):
        return False
    return len(folded) == len(wanted) or not folded[len(wanted)].isalnum()


def short_form_definitions(texts: Iterable[str]) -> list[tuple[str, str]]:
    """Each "short = term" as (short form, the text from its term to the next definition)."""
    definitions: list[tuple[str, str]] = []
    for text in texts:
        matches = list(_SHORT_FORM.finditer(text))
        if not matches:
            continue
        ends = [following.start() for following in matches[1:]] + [len(text)]
        definitions.extend(
            (match.group(1), text[match.end() : end])
            for match, end in zip(matches, ends, strict=True)
        )
    return definitions


# Where a defined term ends: punctuation or a line break.
_TERM_END = re.compile(r"[,;:.()\n]")


def defined_short_forms(texts: Iterable[str]) -> list[tuple[str, str]]:
    """Each "short = term" as (short form, term).

    The term runs to the first punctuation or line break. A term that runs straight into the
    next definition ends with the word that joins the two, such as "och" or "and", which is
    left out.
    """
    pairs: list[tuple[str, str]] = []
    for text in texts:
        matches = list(_SHORT_FORM.finditer(text))
        for match, following in zip(matches, [*matches[1:], None], strict=False):
            rest = text[match.end() : following.start() if following else len(text)]
            words = _TERM_END.split(rest, maxsplit=1)[0].split()
            if following is not None and len(words) > 1 and words[-1].casefold() in {"och", "and"}:
                words = words[:-1]
            if words:
                pairs.append((match.group(1), " ".join(words)))
    return pairs


def slash_alternatives(value: str) -> tuple[str, ...]:
    """The parts of a facit form that joins worded alternatives with a slash."""
    parts = tuple(part.strip() for part in value.split("/"))
    if len(parts) < 2 or not all(any(c.isalpha() for c in part) for part in parts):
        return ()
    return parts


# Typographic apostrophes and quotes, and the keyboard character a student types for each.
_KEYBOARD_PUNCTUATION = str.maketrans(
    {"\u2019": "'", "\u2018": "'", "\u02bc": "'", "\u201c": '"', "\u201d": '"', "\u201e": '"'}
)


def _is_sentence(form: str) -> bool:
    """A form of three or more words that starts with a letter, as a whole sentence does."""
    stripped = form.strip()
    return len(stripped.split()) >= 3 and stripped[:1].isalpha()


def _other_closing_stop(form: str) -> str:
    stripped = form.rstrip()
    return stripped[:-1].rstrip() if stripped.endswith(".") else f"{stripped}."


def _accepted_forms(values: tuple[str, ...], definitions: list[tuple[str, str]]) -> tuple[str, ...]:
    forms = list(values)
    forms.extend(part for value in values for part in slash_alternatives(value))
    for short, term in definitions:
        if short.casefold() in {form.strip().casefold() for form in forms}:
            forms.append(term)
        if any(defines(term, form) for form in forms):
            forms.append(short)
    forms.extend(form.translate(_KEYBOARD_PUNCTUATION) for form in tuple(forms))
    forms.extend(form.replace("'", "\u2019") for form in tuple(forms))
    forms.extend(_other_closing_stop(form) for form in tuple(forms) if _is_sentence(form))
    return tuple(dict.fromkeys(forms))


def with_accepted_forms(item: ProducedItem, context: Iterable[DocxChunk]) -> ProducedItem:
    """Rule 3: each gap also accepts the forms its facit admits; no model value is removed.

    A gap accepts each part of a facit form that joins alternatives with a slash, both
    halves of a "short = term" an instruction defines when the facit gives either, the keyboard
    spelling of a form printed with a typographic apostrophe or quote, and the typographic
    apostrophe of a form spelled with the keyboard one. A sentence form of three or
    more words is accepted with and without a closing full stop.
    """
    definitions = defined_short_forms(chunk.text for chunk in context)
    body = []
    for paragraph in item.body:
        segments = tuple(
            segment.model_copy(
                update={"accepted_values": _accepted_forms(segment.accepted_values, definitions)}
            )
            for segment in paragraph.segments
        )
        body.append(paragraph.model_copy(update={"segments": segments}))
    return item.model_copy(update={"body": tuple(body)})


def _printed_hint(hint: str, source: str) -> str:
    return f" ({hint})" if f"({hint.strip()})" in source else f" {hint}"


def with_printed_hints(item: ProducedItem, sources: Iterable[DocxChunk]) -> ProducedItem:
    """A cue printed beside a blank is student-visible text after the gap, never a hidden hint."""
    source = _normalized(" ".join(chunk.text for chunk in sources))
    body = []
    for paragraph in item.body:
        printed = _normalized(" ".join(s.text for s in paragraph.segments if s.text))
        segments: list[ProducedSegment] = []
        for segment in paragraph.segments:
            if segment.kind != "gap" or not segment.hint:
                segments.append(segment)
                continue
            hint = _normalized(segment.hint)
            segments.append(segment.model_copy(update={"hint": None}))
            if hint not in printed:
                text = _printed_hint(hint, source)
                segments.append(
                    ProducedSegment(kind="text", text=text, accepted_values=(), hint=None)
                )
        body.append(paragraph.model_copy(update={"segments": tuple(segments)}))
    return item.model_copy(update={"body": tuple(body)})


# A printed point label: "(2 p)", "(1 point)" or "Total: 38 poäng".
POINT_LABEL = re.compile(
    r"\(\s*\d+(?:[.,]\d+)?\s*(?:p|poäng|points?|pts?)\.?\s*\)"
    r"|\b\d+(?:[.,]\d+)?\s*(?:poäng|points?)\b",
    re.IGNORECASE,
)
_WORD = re.compile(r"\w+")


def points_line(text: str) -> bool:
    """A line that prints points and at most a two-word label, such as "Total: 38 poäng"."""
    rest = POINT_LABEL.sub(" ", text)
    return rest != text and len(_WORD.findall(rest)) < 3


# A question number printed before the question: an optional one-word prefix, a number of up to
# three digits, then a closing mark, the end of the line, or the points label that follows it.
_NUMBER_LABEL = re.compile(
    r"^\s*((?:[^\W\d_]+\s+)?\d{1,3})(?!\w)(?=\s*(?:[.):]|[(\u2013\u2014-]|$))\s*([.):])?"
)
# A points label printed in parentheses, which no sentence of question text is.
_PARENTHESIZED_POINTS = re.compile(
    r"\(\s*\d+(?:[.,]\d+)?\s*(?:p|poäng|points?|pts?)\.?\s*\)", re.IGNORECASE
)


def _shown_texts(item: ProducedItem) -> list[str]:
    return [
        item.title or "",
        *(s.text or "" for p in item.body for s in p.segments),
        *(choice.text for choice in item.choices),
        *item.match_left,
        *item.match_right,
    ]


def _marker_free_texts(item: ProducedItem) -> list[str]:
    """Texts that print no blank marker; the prompt of a choice item keeps its response position."""
    if item.kind in _CHOICE_KINDS:
        return [item.title or "", *(choice.text for choice in item.choices)]
    return _shown_texts(item)


def _first_body_text(item: ProducedItem) -> str:
    segments = item.body[0].segments if item.body else ()
    return segments[0].text or "" if segments else ""


def _starts_with_label(text: str, label: str, mark: str | None) -> bool:
    shown = _normalized(text)
    if not shown.startswith(label):
        return False
    rest = shown[len(label) :]
    if mark:
        return not rest or rest.startswith(mark)
    return not rest or not rest[0].isalnum()


def label_rule_violation(item: ProducedItem, sources: Iterable[DocxChunk]) -> str | None:
    """Rule 8: the platform numbers and scores questions, so printed labels stay out of the text.

    A question number the first own chunk prints (a number, with at most one word before
    it) does not open the title or the first body line, no points label an own chunk
    prints appears in the title, body, options or match lists, and no blank marker is
    printed in the title, options or match lists, nor in the body of a non-choice item.
    """
    if item.outcome == "review":
        return None
    sources = tuple(sources)
    opening = _NUMBER_LABEL.match(sources[0].text) if sources else None
    if opening is not None:
        label, mark = _normalized(opening.group(1)), opening.group(2)
        if any(
            _starts_with_label(t, label, mark) for t in (item.title or "", _first_body_text(item))
        ):
            return (
                f"its title or first line still begins with the question number that "
                f"{sources[0].anchor} prints: the platform numbers the questions, so leave the "
                "printed number out"
            )
    shown = _normalized(" ".join(_shown_texts(item)))
    for chunk in sources:
        labels = POINT_LABEL if points_line(chunk.text) else _PARENTHESIZED_POINTS
        if any(_normalized(label) in shown for label in labels.findall(chunk.text)):
            return (
                f"its text still prints the points label that {chunk.anchor} shows: the "
                "points belong in the points field, so leave the printed label out"
            )
    printed = sum(len(_BLANK_MARKER.findall(text)) for text in _marker_free_texts(item))
    if printed:
        return (
            f"its title, text, options or match lists still print {printed} blank marker(s) "
            "(an underscore run, dotted line or empty brackets): the platform draws the "
            "answer field itself, so leave the printed marker out"
        )
    return None


def defined_terms(text: str) -> tuple[str, ...]:
    """The terms an instruction defines: each "short = term" pair, or a list after a colon."""
    terms = [
        word
        for short, rest in short_form_definitions((text,))
        for word in (short, *rest.split()[:1])
    ]
    _, colon, listed = text.partition(":")
    parts = [part.strip(" .") for part in re.split(r"[,;]", listed)] if colon else []
    if len([part for part in parts if part]) >= 2:
        terms.extend(part for part in parts if part)
    return tuple(term.strip(" ,;.") for term in terms if term.strip(" ,;."))


def uses_term(terms: Iterable[str], sources: Iterable[DocxChunk]) -> bool:
    """Whether a chunk names one of the terms as a whole word, facit included."""
    text = " ".join(chunk.marked_text for chunk in sources).casefold()
    return any(re.search(rf"(?<!\w){re.escape(term.casefold())}(?!\w)", text) for term in terms)
