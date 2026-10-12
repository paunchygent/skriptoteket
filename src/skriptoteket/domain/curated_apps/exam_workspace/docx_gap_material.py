"""A gap holds what the student supplies, never the material the line talks about (D43).

When a line sets several phrases apart in the same way, one of them can be the material the
line talks about. A set-apart phrase of several words that ends a sentence while its line goes
on in lowercase is such material: the line treats the whole sentence as a name it says
something about, so the student reads it and never writes it. A gap_fill reply that makes such
a phrase a gap could not tell the phrases apart, and the question goes to teacher review.
"""

import re
from collections.abc import Iterable

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import ProducedItem
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk

_SET_APART = re.compile(r"<i>(.*?)</i>", re.S)
_SENTENCE_END = (".", "!", "?")

GAPPED_MATERIAL_REASON = (
    "Frågan markerar flera fraser på samma sätt, och AI-tolkningen gjorde en fras som frågan "
    "talar om till en lucka. Avgör vilka fraser eleven ska skriva och vilka som ska stå kvar "
    "som text. Fras som blev lucka:"
)


def _mentioned_sentences(chunk: DocxChunk) -> frozenset[str]:
    """Set-apart phrases of several words in ``chunk`` that end a sentence while their line
    goes on in lowercase; only a chunk that sets several phrases apart has them. One word with a
    full stop, such as an ordinal or an abbreviation, is no sentence."""
    runs = tuple(_SET_APART.finditer(chunk.marked_text))
    if len(runs) < 2:
        return frozenset()
    found: set[str] = set()
    for run in runs:
        phrase = run.group(1).strip()
        following = chunk.marked_text[run.end() :].lstrip(" \t")[:1]
        sentence = " " in phrase and phrase.endswith(_SENTENCE_END)
        if sentence and following.isalpha() and following.islower():
            found.add(phrase)
    return frozenset(found)


def gapped_material(produced: ProducedItem, chunks: Iterable[DocxChunk]) -> tuple[str, ...]:
    """The material phrases of ``chunks`` that ``produced`` makes gaps, in body order."""
    material = frozenset().union(*(_mentioned_sentences(chunk) for chunk in chunks))
    return tuple(
        dict.fromkeys(
            value.strip()
            for paragraph in produced.body
            for segment in paragraph.segments
            if segment.kind == "gap"
            for value in segment.accepted_values
            if value.strip() in material
        )
    )
