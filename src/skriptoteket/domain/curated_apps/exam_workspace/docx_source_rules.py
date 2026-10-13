"""Text transforms over converter output and source chunks; none rejects a response.

Strips answer-key wording from titles, widens each gap's accepted forms (slash
alternatives, "short = term" definitions, keyboard punctuation) and reads the printed
point labels and defined terms of source instructions.
"""

import re
from collections.abc import Iterable

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
    ProducedItem,
    ProducedSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.errors import validation_error

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


_LABEL_RUN = re.compile(r"\s*(?:" + POINT_LABEL.pattern + ")", re.IGNORECASE)


def _printed_points(label: str) -> int | float | None:
    number = re.search(r"\d+(?:[.,]\d+)?", label)
    if number is None:
        return None
    value = float(number.group().replace(",", "."))
    if value <= 0:
        return None
    return int(value) if value.is_integer() else value


def _without_label(text: str) -> str:
    stripped = _LABEL_RUN.sub("", text)
    return stripped.lstrip() if _LABEL_RUN.match(text) else stripped


def _joined_text_runs(segments: Iterable[ProducedSegment]) -> list[ProducedSegment]:
    """Adjacent text segments as one, so a label split across them leaves as a whole."""
    joined: list[ProducedSegment] = []
    for segment in segments:
        last = joined[-1] if joined else None
        if segment.kind == "text" and last is not None and last.kind == "text":
            text = (last.text or "") + (segment.text or "")
            joined[-1] = last.model_copy(update={"text": text})
        else:
            joined.append(segment)
    return joined


def with_printed_points(item: ProducedItem, own: Iterable[DocxChunk]) -> ProducedItem:
    """D3: a reply without points takes the one points label its own chunks print.

    The label, such as "(1 p)", leaves the item's title and stem text. With no label, or with
    two or more, the item keeps the reply's reading.
    """
    if item.points is not None:
        return item
    labels = [label.group() for chunk in own for label in POINT_LABEL.finditer(chunk.text)]
    points = _printed_points(labels[0]) if len(labels) == 1 else None
    if points is None:
        return item
    body = []
    for paragraph in item.body:
        segments = tuple(
            segment.model_copy(update={"text": _without_label(segment.text)})
            if segment.kind == "text" and segment.text
            else segment
            for segment in _joined_text_runs(paragraph.segments)
        )
        body.append(paragraph.model_copy(update={"segments": segments}))
    title = _without_label(item.title).strip() if item.title else item.title
    return item.model_copy(update={"points": points, "body": tuple(body), "title": title or None})
