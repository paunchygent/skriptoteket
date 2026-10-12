"""Evaluator-only projection of gold items onto source chunk anchors.

Gold carries no anchors, so the evaluator derives a chunk-level reference by
aligning chunk lines with gold text in source order. This module runs only
after provider output exists; nothing here is ever sent to a model.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field

from scripts.exam_conversion_eval.gold import GoldExam, GoldItem
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk

_TAG = re.compile(r"<[^>]+>")
_WORD = re.compile(r"\w+", re.UNICODE)
_LOOKAHEAD = 3


def tokens(text: str) -> list[str]:
    text = unicodedata.normalize("NFKC", _TAG.sub(" ", text)).replace("[___]", " ")
    return [token for token in _WORD.findall(text.lower()) if token.strip("_")]


def _f1(left: list[str], right: list[str]) -> float:
    common = sum((Counter(left) & Counter(right)).values())
    if common == 0:
        return 0.0
    precision, recall = common / len(left), common / len(right)
    return 2 * precision * recall / (precision + recall)


def _contained(small: list[str], big: list[str]) -> bool:
    return sum((Counter(small) & Counter(big)).values()) >= 0.85 * len(small)


def _covers(line: list[str], unit: list[str]) -> bool:
    """The chunk line and the gold unit carry the same text, allowing a short label or points tag."""
    if line == unit:
        return True
    if len(unit) <= 3 or len(line) <= 3:
        extra = list((Counter(line) - Counter(unit)).elements())
        wordy = [token for token in extra if not token.isdigit()]
        return (
            _contained(unit, line)
            and len(extra) <= 3
            and len(wordy) <= (1 if len(unit) == 1 else 3)
        )
    return _f1(line, unit) >= 0.8 or (_contained(unit, line) and len(line) <= len(unit) + 4)


@dataclass
class _ItemUnits:
    label: list[str]
    prompt_lines: list[list[str]]
    content: list[list[str]]
    values: list[list[str]]
    notes: list[list[str]]
    correct: list[list[str]]

    def own_units(self) -> list[list[str]]:
        return self.content[len(self.prompt_lines) :] + self.prompt_lines[1:]

    def key_covers(self, line: list[str]) -> bool:
        """The line is keyed content of the item plus at most a short label."""
        vocabulary = {token for unit in self.values for token in unit}
        inside = [token for token in line if token in vocabulary]
        if len(line) - len(inside) <= 4 and any(_contained(unit, line) for unit in self.values):
            return True
        return any(_f1(line, note) >= 0.6 or _contained(line, note) for note in self.notes)


def _units(item: GoldItem) -> _ItemUnits:
    prompt_lines = [t for t in (tokens(line) for line in item.prompt.split("\n")) if t]
    content = prompt_lines + [tokens(choice) for choice in item.choices]
    content += [tokens(pair.left) for pair in item.pairs]
    values = [tokens(value) for value in item.correct_choices]
    values += [tokens(value) for gap in item.gaps for value in gap.accepted_values]
    values += [tokens(pair.right) for pair in item.pairs]
    return _ItemUnits(
        label=tokens(item.source_label),
        prompt_lines=prompt_lines,
        content=[unit for unit in content if unit],
        values=[unit for unit in values if unit],
        notes=[unit for unit in (tokens(note) for note in item.notes) if unit],
        correct=[tokens(value) for value in item.correct_choices]
        + [tokens(pair.right) for pair in item.pairs],
    )


def _chunk_lines(chunk: DocxChunk) -> list[list[str]]:
    separator = r"\n|\|" if chunk.kind == "table" else r"\n"
    return [t for t in (tokens(part) for part in re.split(separator, chunk.marked_text)) if t]


@dataclass
class ReferenceItem:
    index: int
    source_label: str
    kind: str
    points: float | None
    content: list[str] = field(default_factory=list)
    key: list[str] = field(default_factory=list)
    contexts: list[str] = field(default_factory=list)

    @property
    def owned(self) -> set[str]:
        return set(self.content) | set(self.key)


@dataclass
class Reference:
    exam: str
    items: list[ReferenceItem]
    title: list[str]
    shared: dict[str, list[int]]
    unmatched: dict[str, int | None]
    letter_keys: list[str]
    roles: dict[str, str]

    def owner_of(self) -> dict[str, int]:
        return {anchor: item.index for item in self.items for anchor in item.owned}

    def to_json(self) -> dict[str, object]:
        return {
            "exam": self.exam,
            "title": self.title,
            "items": [vars(item) for item in self.items],
            "shared": self.shared,
            "unmatched": self.unmatched,
            "letter_keys": self.letter_keys,
            "roles": self.roles,
        }


class _Projector:
    def __init__(self, exam: str, gold: GoldExam, chunks: tuple[DocxChunk, ...]):
        self.chunks = chunks
        self.units = [_units(item) for item in gold.questions]
        self.title_tokens = tokens(gold.title)
        counts = Counter(token for chunk in chunks for token in set(tokens(chunk.marked_text)))
        self.frequent = {token for token, count in counts.items() if count >= 3}
        self.ref = Reference(
            exam=exam,
            items=[
                ReferenceItem(index, item.source_label, item.kind, item.points)
                for index, item in enumerate(gold.questions)
            ],
            title=[],
            shared={},
            unmatched={},
            letter_keys=[],
            roles={},
        )
        self.used: list[set[int]] = [set() for _ in gold.questions]
        self.current = -1
        self.content_lines: dict[int, list[list[str]]] = {}

    def prompt_hits(self, index: int, lines: list[list[str]]) -> list[int]:
        return [
            position
            for position, unit in enumerate(self.units[index].prompt_lines)
            if any(_covers(line, unit) for line in lines)
        ]

    def content_hit(self, index: int, lines: list[list[str]]) -> bool:
        return any(_covers(line, unit) for unit in self.units[index].content for line in lines)

    def label_names(self, index: int, lines: list[list[str]]) -> bool:
        """The chunk names the item's numbered label and adds only digits or recurring tags."""
        label = self.units[index].label
        if len(label) < 2 or not any(token.isdigit() for token in label):
            return False
        for line in lines:
            if _contained(label, line) and len(label) <= len(line) <= len(label) + 4:
                extra = (Counter(line) - Counter(label)).elements()
                own = {token for unit in self.units[index].prompt_lines for token in unit}
                if all(
                    token.isdigit() or token in self.frequent or token in own for token in extra
                ):
                    return True
        return False

    def next_owns(self, lines: list[list[str]]) -> bool:
        """The chunk carries text of the next item that the current item does not also carry."""
        nxt = self.current + 1
        if nxt >= len(self.units):
            return False
        current_units = self.units[self.current] if self.current >= 0 else None
        for line in lines:
            if not any(_covers(line, unit) for unit in self.units[nxt].own_units()):
                continue
            if current_units is None or not any(
                _covers(line, unit) for unit in current_units.content
            ):
                return True
        return False

    def repeats_current(self, lines: list[list[str]]) -> bool:
        """Every matched line is one the current item already carried: a per-item repeat."""
        matched = [
            line
            for line in lines
            if any(_covers(line, unit) for unit in self.units[self.current + 1].prompt_lines)
        ]
        return bool(matched) and all(
            any(_covers(line, unit) for unit in self.units[self.current].prompt_lines)
            for line in matched
        )

    def spent_on_current(self, lines: list[list[str]]) -> bool:
        """The chunk repeats prompt lines the current item already used and the next item still needs."""
        nxt = self.current + 1
        if nxt >= len(self.units) or self.content_hit_beyond_prompt(self.current, lines):
            return False
        hits = self.prompt_hits(self.current, lines)
        fresh_next = [p for p in self.prompt_hits(nxt, lines) if p not in self.used[nxt]]
        return bool(hits) and all(p in self.used[self.current] for p in hits) and bool(fresh_next)

    def choice_lines(self, index: int, lines: list[list[str]]) -> int:
        units = self.units[index].content[len(self.units[index].prompt_lines) :]
        return sum(any(_covers(line, unit) for unit in units) for line in lines)

    def content_hit_beyond_prompt(self, index: int, lines: list[list[str]]) -> bool:
        units = self.units[index].content[len(self.units[index].prompt_lines) :]
        return any(_covers(line, unit) for unit in units for line in lines)

    def assign(self, anchor: str, index: int, role: str, lines: list[list[str]]) -> None:
        item = self.ref.items[index]
        (item.key if role == "answer_key" else item.content).append(anchor)
        self.ref.roles[anchor] = role
        self.used[index].update(self.prompt_hits(index, lines))
        if role != "answer_key":
            self.content_lines.setdefault(index, []).extend(lines)

    def letter_key(self, lines: list[list[str]]) -> bool:
        """A short line naming option letters whose option lines are the item's correct choices."""
        flat = [token for line in lines for token in line]
        letters = [token for token in flat if len(token) == 1 and token.isalpha()]
        others = [token for token in flat if token not in letters and not token.isdigit()]
        if not letters or len(others) > 3:
            return False
        options = {
            line[0]: line[1:] for line in self.content_lines.get(self.current, []) if len(line) > 1
        }
        correct = self.units[self.current].correct
        return all(
            letter in options and any(_covers(options[letter], unit) for unit in correct)
            for letter in letters
        )

    def run(self) -> Reference:
        for chunk in self.chunks:
            self.place(chunk.anchor, _chunk_lines(chunk), chunk.marked_text)
        return self.ref

    def place(self, anchor: str, lines: list[list[str]], text: str) -> None:
        ref, current = self.ref, self.current
        if not ref.title and current < 0 and _f1(tokens(text), self.title_tokens) >= 0.8:
            ref.title.append(anchor)
            ref.roles[anchor] = "title"
            return
        choice_lines = current >= 0 and self.choice_lines(current, lines) >= 2
        if (
            current >= 0
            and lines
            and not choice_lines
            and all(self.units[current].key_covers(line) for line in lines)
        ):
            hits = self.prompt_hits(current, lines)
            if all(position in self.used[current] for position in hits):
                self.assign(anchor, current, "answer_key", lines)
                return
        window = range(current + 1, min(current + 1 + _LOOKAHEAD, len(self.units)))
        named = [index for index in window if self.label_names(index, lines)]
        fresh = current >= 0 and any(
            position not in self.used[current] for position in self.prompt_hits(current, lines)
        )
        run: list[int] = []
        for index in range(current + 1, len(self.units)):
            if not self.prompt_hits(index, lines):
                break
            run.append(index)
        next_owns = self.next_owns(lines)
        if len(run) >= 2 and not fresh and not next_owns:
            if current >= 0 and self.repeats_current(lines):
                self.current = current + 1
                self.assign(anchor, current + 1, "question_start", lines)
                return
            if named:
                self.current = named[0]
                self.assign(anchor, named[0], "question_start", lines)
                return
            ref.shared[anchor] = run
            ref.roles[anchor] = "shared_context"
            for index in run:
                ref.items[index].contexts.append(anchor)
                self.used[index].update(self.prompt_hits(index, lines))
            return
        spent = current >= 0 and self.spent_on_current(lines)
        if fresh or (
            current >= 0 and self.content_hit(current, lines) and not next_owns and not spent
        ):
            self.assign(anchor, current, "question_content", lines)
            return
        if spent:
            self.current = current + 1
            self.assign(anchor, current + 1, "question_start", lines)
            return
        later = [index for index in window if self.content_hit(index, lines)]
        if later:
            self.current = later[0]
            self.assign(anchor, later[0], "question_start", lines)
            return
        if current >= 0 and (
            any(self.units[current].key_covers(line) for line in lines) or self.letter_key(lines)
        ):
            if self.letter_key(lines):
                ref.letter_keys.append(anchor)
            self.assign(anchor, current, "answer_key", lines)
            return
        if named:
            self.current = named[0]
            self.assign(anchor, named[0], "question_start", lines)
            return
        if current >= 0 and _mostly_item_text(self.units[current], lines):
            self.assign(anchor, current, "question_content", lines)
            return
        ref.unmatched[anchor] = current if current >= 0 else None
        ref.roles[anchor] = "unmatched"


def _mostly_item_text(item_units: _ItemUnits, lines: list[list[str]]) -> bool:
    """A mixed line that interleaves the item's prompt and keyed text."""
    vocabulary = {token for unit in item_units.content + item_units.values for token in unit}
    flat = [token for line in lines for token in line]
    return len(flat) >= 4 and sum(token in vocabulary for token in flat) >= 0.7 * len(flat)


def project(exam: str, gold: GoldExam, chunks: tuple[DocxChunk, ...]) -> Reference:
    return _Projector(exam, gold, chunks).run()
