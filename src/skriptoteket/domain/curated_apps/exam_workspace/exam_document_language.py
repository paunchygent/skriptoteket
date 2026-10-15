"""Infer one language for a whole exam document (TASK-SKRIPT-39-09-06).

The producer never mixes languages per value: the document text decides once.
Stopword counts are the primary signal; an å/ä/ö occurrence adds one Swedish
point, and the product's Swedish-first default wins every tie.
"""

import re
from typing import Literal

Language = Literal["sv", "en"]

_WORD_PATTERN = re.compile(r"[^\W\d_]+", re.UNICODE)
_SWEDISH_LETTERS = frozenset("åäö")

_SWEDISH_STOPWORDS = frozenset(
    """
    alla allt alltid aldrig att av bara blev blir bland borde
    då där därför efter eftersom eller en ett fast fick flera
    före för genom gjorde gör hade han har henne hennes hon hur
    här ibland inte jag ju kan kunde man med mellan men mig
    mot många måste ned nej ni nu när och om oss också på
    samma sedan sig sin sina ska skulle som så till trots under
    upp ur ut utan vad var varför varit vem vet vi vid vilka vilken
    vilket vill väl än är åt över
    """.split()
)

_ENGLISH_STOPWORDS = frozenset(
    """
    a about after all also am an and any are as at be been before
    being between both but by can could did do does doing down during
    each few for from further had has have having he her here hers
    him his how if in into is it its just may me might more most
    much must my no nor not of off on once only or other our out
    over own same she should so some such than that the their them
    then there these they this those through to too until up
    very was we were what when where which while who whom why will
    with would you your
    """.split()
)


def infer_exam_document_language(text: str) -> Language:
    """Return "sv" or "en" for the whole document; ties go to Swedish."""
    folded = text.casefold()
    tokens = _WORD_PATTERN.findall(folded)
    swedish = sum(token in _SWEDISH_STOPWORDS for token in tokens)
    english = sum(token in _ENGLISH_STOPWORDS for token in tokens)
    if any(letter in folded for letter in _SWEDISH_LETTERS):
        swedish += 1
    return "sv" if swedish >= english else "en"
