"""Grouping pass output for the DOCX conversion lane: source references only.

TASK-SKRIPT-39-05-04 step 1. The grouping model returns anchors, never text.
``manifest_from_output`` validates and normalises that output against the chunk
anchors, and ``question_source`` reads one question's source markdown back from
the chunks. Code adds or removes no text (D14).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal, get_args

from pydantic import JsonValue

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk

ContextScope = Literal[
    "section_instruction", "shared_passage", "word_bank", "exam_metadata", "other"
]
_SCOPES: frozenset[str] = frozenset(get_args(ContextScope))
HeaderKind = Literal["course", "part_total", "question_total"]
_HEADER_KINDS: frozenset[str] = frozenset(get_args(HeaderKind))
_EXAM_OWNER = "exam"


class ManifestInvalid(ValueError):
    """The grouping output cannot become a manifest; ``code`` names why."""

    def __init__(self, code: str, detail: str = "") -> None:
        self.code = code
        super().__init__(f"{code}: {detail}" if detail else code)


@dataclass(frozen=True)
class ManifestQuestion:
    question_id: str
    anchors: tuple[str, ...]
    subpart_anchors: tuple[str, ...]
    key_anchors: tuple[str, ...]


@dataclass(frozen=True)
class SharedContext:
    anchor: str
    scope: ContextScope
    owner: str
    governs: tuple[str, ...]


@dataclass(frozen=True)
class HeaderAnchor:
    """A source header line: exam metadata, never exam text (TASK-SKRIPT-39-05-14 D1).

    ``governs`` names the questions of a part or question total; it is empty for the course line.
    Code reads the exam total from the source text, so it has no header kind.
    """

    anchor: str
    kind: HeaderKind
    governs: tuple[str, ...]


@dataclass(frozen=True)
class ExamManifest:
    questions: tuple[ManifestQuestion, ...]
    contexts: tuple[SharedContext, ...]
    title_anchors: tuple[str, ...]
    header: tuple[HeaderAnchor, ...]
    invalid_anchors: tuple[str, ...]
    duplicate_anchors: tuple[str, ...]
    unplaced_anchors: tuple[str, ...]

    def question(self, question_id: str) -> ManifestQuestion:
        for question in self.questions:
            if question.question_id == question_id:
                return question
        raise KeyError(question_id)


def _shape(detail: str) -> ManifestInvalid:
    return ManifestInvalid("manifest_shape", detail)


def _entries(raw: Mapping[str, JsonValue], key: str) -> list[Mapping[str, JsonValue]]:
    value = raw.get(key)
    if not isinstance(value, list):
        raise _shape(key)
    entries: list[Mapping[str, JsonValue]] = []
    for entry in value:
        if not isinstance(entry, dict):
            raise _shape(key)
        entries.append(entry)
    return entries


def _strings(entry: Mapping[str, JsonValue], key: str) -> tuple[str, ...]:
    value = entry.get(key)
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise _shape(key)
    return tuple(item for item in value if isinstance(item, str))


def _string(entry: Mapping[str, JsonValue], key: str) -> str:
    value = entry.get(key)
    if not isinstance(value, str):
        raise _shape(key)
    return value


class _Placement:
    """Places each known chunk anchor at most once and records the rest."""

    def __init__(self, known: frozenset[str]) -> None:
        self._known = known
        self.placed: set[str] = set()
        self.invalid: list[str] = []
        self.duplicate: list[str] = []

    def claim(self, anchors: tuple[str, ...]) -> list[str]:
        kept: list[str] = []
        for anchor in anchors:
            if anchor not in self._known:
                self.invalid.append(anchor)
            elif anchor in self.placed:
                self.duplicate.append(anchor)
            else:
                self.placed.add(anchor)
                kept.append(anchor)
        return kept

    def invalid_only(self, anchors: tuple[str, ...]) -> None:
        self.invalid.extend(anchor for anchor in anchors if anchor not in self._known)


def manifest_from_output(
    raw: Mapping[str, JsonValue], chunks: tuple[DocxChunk, ...]
) -> ExamManifest:
    """Validate grouping output against the chunk anchors and normalise it."""
    positions = {chunk.anchor: index for index, chunk in enumerate(chunks)}
    title = _strings(raw, "title_anchors")
    header_entries = [
        (_string(entry, "anchor"), _string(entry, "kind"), _strings(entry, "governs"))
        for entry in _entries(raw, "header_anchors")
    ]
    for _anchor, kind, _governs in header_entries:
        if kind not in _HEADER_KINDS:
            raise _shape(f"header kind {kind}")
    question_entries = [
        (
            _string(entry, "id"),
            _strings(entry, "anchors"),
            _strings(entry, "subpart_anchors"),
            _strings(entry, "answer_key_anchors"),
        )
        for entry in _entries(raw, "questions")
    ]
    context_entries = [
        (
            _string(entry, "anchor"),
            _string(entry, "scope"),
            _string(entry, "owner"),
            _strings(entry, "governs"),
        )
        for entry in _entries(raw, "shared_contexts")
    ]
    for _anchor, scope, _owner, _governs in context_entries:
        if scope not in _SCOPES:
            raise _shape(f"scope {scope}")

    placement = _Placement(frozenset(positions))
    seen_ids: set[str] = set()
    kept: list[tuple[str, list[str], list[str], list[str]]] = []
    for question_id, anchors, subparts, keys in question_entries:
        if question_id in seen_ids:
            continue
        seen_ids.add(question_id)
        own = placement.claim(anchors)
        if own:
            # An own chunk the question also lists as its key stays its own chunk and keeps
            # the facit mark: it is the question's key unless the converted item holds it.
            facit = [*dict.fromkeys(k for k in keys if k in own)]
            claimed = placement.claim(tuple(k for k in keys if k not in own))
            kept.append((question_id, own, list(dict.fromkeys(subparts)), [*facit, *claimed]))
        else:
            placement.invalid_only(keys)

    contexts_kept: list[tuple[str, str, str, tuple[str, ...]]] = []
    for anchor, scope, owner, governs in context_entries:
        if placement.claim((anchor,)):
            contexts_kept.append((anchor, scope, owner, governs))
    kept_title = tuple(placement.claim(title))
    header_kept = [
        (anchor, kind, governs)
        for anchor, kind, governs in header_entries
        if placement.claim((anchor,))
    ]
    # A subpart the model lists only as a subpart, and places nowhere else, is one of its
    # question's own chunks.
    for _question_id, owned, listed, _keys in kept:
        unplaced = tuple(s for s in listed if s in positions and s not in placement.placed)
        owned.extend(placement.claim(unplaced))
        listed[:] = [s for s in listed if s in owned]

    def position(anchor: str) -> int:
        return positions[anchor]

    ordered = sorted(kept, key=lambda item: min(map(position, item[1])))
    questions = tuple(
        ManifestQuestion(
            question_id=question_id,
            anchors=tuple(sorted(own, key=position)),
            subpart_anchors=tuple(sorted(subparts, key=position)),
            key_anchors=tuple(sorted(keys, key=position)),
        )
        for question_id, own, subparts, keys in ordered
    )
    if not questions:
        raise ManifestInvalid("manifest_empty", "no question kept")
    ids = [question.question_id for question in questions]
    contexts = tuple(
        SharedContext(
            anchor=anchor,
            scope=_scope(scope),
            owner=owner if owner in ids else _EXAM_OWNER,
            governs=tuple(question_id for question_id in ids if question_id in governs),
        )
        for anchor, scope, owner, governs in contexts_kept
    )
    return ExamManifest(
        questions=questions,
        contexts=contexts,
        title_anchors=kept_title,
        header=tuple(
            HeaderAnchor(
                anchor=anchor,
                kind=_header_kind(kind),
                governs=(
                    tuple(q for q in ids if q in governs)
                    if kind in {"part_total", "question_total"}
                    else ()
                ),
            )
            for anchor, kind, governs in header_kept
        ),
        invalid_anchors=tuple(placement.invalid),
        duplicate_anchors=tuple(placement.duplicate),
        unplaced_anchors=tuple(a for a in positions if a not in placement.placed),
    )


def _scope(scope: str) -> ContextScope:
    scopes: tuple[ContextScope, ...] = get_args(ContextScope)
    for allowed in scopes:
        if scope == allowed:
            return allowed
    raise _shape(f"scope {scope}")


def _header_kind(kind: str) -> HeaderKind:
    kinds: tuple[HeaderKind, ...] = get_args(HeaderKind)
    for allowed in kinds:
        if kind == allowed:
            return allowed
    raise _shape(f"header kind {kind}")


def question_source(manifest: ExamManifest, chunks: tuple[DocxChunk, ...], question_id: str) -> str:
    """One question's own chunks, governing context and section heading as source markdown."""
    included = question_source_anchors(manifest, chunks, question_id)
    return "\n".join(chunk.marked_text for chunk in chunks if chunk.anchor in included)


def question_source_anchors(
    manifest: ExamManifest, chunks: tuple[DocxChunk, ...], question_id: str
) -> frozenset[str]:
    """The anchors of one question's own chunks, governing context and section heading."""
    question = manifest.question(question_id)
    positions = {chunk.anchor: index for index, chunk in enumerate(chunks)}
    all_keys = {a for q in manifest.questions for a in q.key_anchors}
    all_questions = {a for q in manifest.questions for a in q.anchors}
    metadata = set(manifest.title_anchors) | {header.anchor for header in manifest.header}
    governing = {
        context.anchor
        for context in manifest.contexts
        if question_id in context.governs
        and context.scope != "exam_metadata"
        and context.anchor not in metadata | all_keys
    }
    included = set(question.anchors) | set(question.key_anchors) | governing
    present = [positions[anchor] for anchor in question.anchors if anchor in positions]
    if present:
        excluded = metadata | all_questions | all_keys
        heading = next(
            (
                chunk.anchor
                for chunk in reversed(chunks[: min(present)])
                if chunk.kind == "heading" and chunk.anchor not in excluded
            ),
            None,
        )
        if heading is not None:
            included.add(heading)
    return frozenset(included)
