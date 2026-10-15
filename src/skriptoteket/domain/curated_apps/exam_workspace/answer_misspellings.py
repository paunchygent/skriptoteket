"""Deterministic misspellings for exam-workspace accepted values (TASK-SKRIPT-39-09-06).

One document language per call; candidates come in tier order -- attested
learner errors, hunspell REP reversal, vendored keyboard neighbours -- and the
existing A10 filter keeps at most three survivors per accepted value. A
candidate present in the committed word-form lexicon, including inflections,
is never emitted. Productive compounds absent from that lexicon are not checked
(user decision 2026-10-15).
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

from skriptoteket.domain.curated_apps.exam_workspace.answer_spelling import (
    filter_answer_spelling_candidates,
    normalize_answer,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_document_language import Language
from skriptoteket.domain.curated_apps.exam_workspace.misspelling_data import (
    LanguageMisspellingData,
    WordFormLexicon,
    load_misspelling_data,
)

_EDGE_PUNCTUATION = re.compile(r"^\W+|\W+$", re.UNICODE)


def produce_answer_misspellings(
    accepted_values: tuple[str, ...],
    *,
    language: Language,
    other_gold_answers: tuple[str, ...] = (),
) -> tuple[str, ...]:
    """Return up to three automatic misspellings per accepted value.

    Each accepted value is ranked on its own, so a candidate generated for one
    value never consumes another value's three slots. The result is
    deterministic, de-duplicated and keeps the accepted values' input order.
    """
    data = load_misspelling_data(language)
    hidden = {normalize_answer(value) for value in (*accepted_values, *other_gold_answers)}
    emitted: list[str] = []
    seen: set[str] = set()
    for value in accepted_values:
        candidates = tuple(
            candidate
            for candidate in _candidates_for(value, data)
            if normalize_answer(candidate) not in hidden
            and not _changes_a_real_word(candidate, value, data.valid_words)
        )
        for kept in filter_answer_spelling_candidates((value,), candidates):
            normalized = normalize_answer(kept)
            if normalized in seen:
                continue
            seen.add(normalized)
            emitted.append(kept)
    return tuple(emitted)


def _candidates_for(value: str, data: LanguageMisspellingData) -> tuple[str, ...]:
    key = normalize_answer(value)
    candidates = list(data.attested.get(key, ()))
    candidates.extend(_rep_candidates(key, data.rep))
    candidates.extend(_keyboard_candidates(key, data.keyboard))
    return tuple(candidates)


def _rep_candidates(word: str, rules: tuple[tuple[str, str], ...]) -> list[str]:
    """Replace one occurrence at a time; hunspell REP's left side becomes the typo.

    A ^ or $ anchor on either side restricts the match to the word's start or
    end; anchors are stripped from the emitted replacement. Whitespace,
    underscore and dot rules never apply.
    """
    candidates: list[str] = []
    for wrong, right in rules:
        replacement = _rep_side(wrong)
        pattern = _rep_side(right)
        if replacement is None or pattern is None:
            continue
        starts = replacement.starts or pattern.starts
        ends = replacement.ends or pattern.ends
        if starts and ends:
            if word == pattern.body:
                candidates.append(replacement.body)
        elif starts:
            if word.startswith(pattern.body):
                candidates.append(replacement.body + word[len(pattern.body) :])
        elif ends:
            if word.endswith(pattern.body):
                candidates.append(word[: len(word) - len(pattern.body)] + replacement.body)
        else:
            start = word.find(pattern.body)
            while start >= 0:
                candidates.append(
                    f"{word[:start]}{replacement.body}{word[start + len(pattern.body) :]}"
                )
                start = word.find(pattern.body, start + 1)
    return candidates


@dataclass(frozen=True)
class _RepSide:
    body: str
    starts: bool
    ends: bool


def _rep_side(value: str) -> _RepSide | None:
    """Return a rule side without its anchors, or None when the rule is excluded."""
    starts = value.startswith("^")
    ends = value.endswith("$")
    body = value.removeprefix("^").removesuffix("$")
    if not body or "^" in body or "$" in body:
        return None
    if any(character.isspace() or character in "_." for character in body):
        return None
    return _RepSide(body=body, starts=starts, ends=ends)


def _keyboard_candidates(word: str, keyboard: Mapping[str, tuple[str, ...]]) -> list[str]:
    """Substitute one adjacent key per position, position then lexical order."""
    candidates: list[str] = []
    for index, char in enumerate(word):
        for neighbour in sorted(keyboard.get(char, ())):
            candidates.append(f"{word[:index]}{neighbour}{word[index + 1 :]}")
    return candidates


def _changes_a_real_word(candidate: str, accepted: str, words: WordFormLexicon) -> bool:
    """True when the candidate is a real word or phrase of the document language.

    A same-length token change is real-word when the changed token's word form
    (punctuation removed) is a known inflected form. A spacing-only variant of
    the same letters stays eligible, except when joining it produces one valid
    word; splitting a compound into valid words keeps the Swedish
    compound-spacing supplement alive. Any other changed structure is real-word
    when every resulting word form is a valid word.
    """
    candidate_tokens = normalize_answer(candidate).split()
    accepted_tokens = normalize_answer(accepted).split()
    word_forms = [_word_form(token) for token in candidate_tokens]
    if len(candidate_tokens) == len(accepted_tokens):
        return any(
            candidate_token != accepted_token and word_form in words
            for candidate_token, accepted_token, word_form in zip(
                candidate_tokens, accepted_tokens, word_forms
            )
        )
    if "".join(candidate_tokens) == "".join(accepted_tokens):
        return len(word_forms) == 1 and word_forms[0] in words
    return all(word_form in words for word_form in word_forms)


def _word_form(token: str) -> str:
    """Return one token without its surrounding punctuation."""
    return _EDGE_PUNCTUATION.sub("", token)
