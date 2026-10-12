"""Provider-facing labeling methods. Inputs are source chunks and model output only; never gold."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any

from scripts.labeling_feasibility.api import (
    CallRecord,
    OpenAIClient,
    decision_answers,
    responses_output_json,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk

MAX_QUESTIONS_PER_REQUEST = 200  # Observed 400 above 200 on 2026-10-11.
GROUPING_MODEL = "gpt-6-luna"

KIND_LABELS: tuple[tuple[str, str], ...] = (
    ("single_choice", "The student chooses exactly one of the listed options."),
    (
        "multiple_response",
        "The student chooses several of the listed options, as the question's response instruction asks.",
    ),
    (
        "gap_fill",
        "The source fixes the response units: answer slots, blanks or fields the student fills in, "
        "including slots filled from a word bank or label list.",
    ),
    ("free_text", "The student writes a response and decides where its units begin and end."),
    (
        "matching",
        "The student pairs entries of one supplied set with entries of another supplied set.",
    ),
    (
        "unsupported",
        "The required interaction cannot be represented by any kind above without changing how the student answers.",
    ),
    ("unresolved", "The source is insufficient or contradictory for a reliable choice."),
)

ROLE_LABELS: tuple[tuple[str, str], ...] = (
    ("title", "The exam title."),
    (
        "question_start",
        "Starts a new question: its number or heading line, or its first stem line when it has no heading. "
        "When a heading starts the question, the stem lines after the heading are question_content.",
    ),
    (
        "question_content",
        "Continues the current question: stem, options, table, answer line or blank, or other text of that question.",
    ),
    ("subpart", "Starts a lettered or numbered subpart that belongs inside the current question."),
    (
        "shared_context",
        "An instruction, passage, word bank or other context that governs several questions.",
    ),
    ("answer_key", "Gives the correct answer, sample answer or grading facit for a question."),
    ("other", "Exam totals, section headings, points lines, metadata or anything else."),
)

SCOPE_LABELS: tuple[tuple[str, str], ...] = (
    ("next_question", "Governs only the question that follows it."),
    (
        "following_run",
        "Governs the questions that follow it until the next shared instruction or section heading.",
    ),
    ("whole_exam", "Governs every question in the exam."),
)

POINT_VALUES = (
    "0.5",
    "1",
    "1.5",
    "2",
    "3",
    "4",
    "5",
    "6",
    "7",
    "8",
    "9",
    "10",
    "12",
    "15",
    "unknown",
)


def render_chunks(chunks: tuple[DocxChunk, ...]) -> str:
    return "\n".join(f"[{chunk.anchor}] ({chunk.kind}) {chunk.marked_text}" for chunk in chunks)


@dataclass
class Question:
    id: str
    anchors: list[str]
    key_anchors: list[str] = field(default_factory=list)
    subpart_anchors: list[str] = field(default_factory=list)


@dataclass
class Context:
    anchor: str
    scope: str
    owner: str
    governs: list[str]


@dataclass
class Grouping:
    method: str
    questions: list[Question]
    contexts: list[Context]
    title: list[str]
    other: list[str]
    invalid_anchors: list[str] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return {
            "method": self.method,
            "questions": [vars(question) for question in self.questions],
            "contexts": [vars(context) for context in self.contexts],
            "title": self.title,
            "other": self.other,
            "invalid_anchors": self.invalid_anchors,
        }

    @classmethod
    def from_json(cls, saved: dict[str, Any]) -> Grouping:
        return cls(
            method=saved["method"],
            questions=[Question(**question) for question in saved["questions"]],
            contexts=[Context(**context) for context in saved["contexts"]],
            title=saved["title"],
            other=saved["other"],
            invalid_anchors=saved["invalid_anchors"],
        )


@dataclass
class MethodResult:
    calls: list[CallRecord]
    output: Any

    def summary(self) -> dict[str, Any]:
        usage = [call.usage for call in self.calls]
        costs = [call.cost_usd() for call in self.calls]
        return {
            "calls": len(self.calls),
            "ok": all(call.ok for call in self.calls),
            "input_tokens": sum(int(u.get("input_tokens") or 0) for u in usage),
            "output_tokens": sum(int(u.get("output_tokens") or 0) for u in usage),
            "reasoning_tokens": sum(
                int((u.get("output_tokens_details") or {}).get("reasoning_tokens") or 0)
                for u in usage
            ),
            "cost_usd": None if any(cost is None for cost in costs) else sum(c for c in costs if c),
            "wall_seconds": max((call.duration_seconds for call in self.calls), default=0.0),
            "sum_call_seconds": sum(call.duration_seconds for call in self.calls),
        }


async def decide(
    client: OpenAIClient,
    label: str,
    input_value: str | list[dict[str, Any]],
    questions: list[dict[str, Any]],
) -> tuple[list[CallRecord], dict[str, dict[str, Any]]]:
    """Send independent questions, split into concurrent requests at the observed size limit."""
    batches = [
        questions[start : start + MAX_QUESTIONS_PER_REQUEST]
        for start in range(0, len(questions), MAX_QUESTIONS_PER_REQUEST)
    ]
    records = await asyncio.gather(
        *(
            client.decisions(label=f"{label}#{index}", input_value=input_value, questions=batch)
            for index, batch in enumerate(batches)
        )
    )
    answers: dict[str, dict[str, Any]] = {}
    for record in records:
        answers.update(decision_answers(record))
    return list(records), answers


def _choices(labels: tuple[tuple[str, str], ...]) -> list[dict[str, str]]:
    return [{"value": value, "description": description} for value, description in labels]


def _short(anchor: str) -> str:
    return anchor.replace("body:", "")


# Grouping A: Responses manifest of source references.

GROUPING_INSTRUCTIONS = """You map the structure of an exam document given as ordered source chunks, each with an anchor.
Return only anchor references. Never write question text, options or answers.

Rules:
- A question is one student task. Its anchors are its number or heading line, stem, options, tables, answer lines or blanks, and all its subparts.
- Subparts (a), b), 1., 2. inside one task) stay inside their parent question. List them in the question's anchors and also in subpart_anchors.
- answer_key_anchors of a question: chunks that give its correct answer, sample answer or grading facit.
- shared_contexts: a chunk with an instruction, passage, word bank or other context that governs several questions, including a section instruction before a run of questions. Give the question ids it governs, its scope, and exactly one owner: "exam" for section- or exam-level text, otherwise the id of the single question it belongs to. A shared chunk never also appears in a question's anchors.
- title_anchors: the exam title. other_anchors: totals, section headings, points lines and other metadata.
- Every input anchor appears exactly once across questions[].anchors, questions[].answer_key_anchors, shared_contexts, title_anchors and other_anchors. subpart_anchors repeat anchors already in the question's anchors.
- Question ids are q1, q2, ... in source order.
- Judge structure from layout, numbering and instructions, not from the subject matter."""

GROUPING_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "title_anchors": {"type": "array", "items": {"type": "string"}},
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "anchors": {"type": "array", "items": {"type": "string"}},
                    "subpart_anchors": {"type": "array", "items": {"type": "string"}},
                    "answer_key_anchors": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["id", "anchors", "subpart_anchors", "answer_key_anchors"],
                "additionalProperties": False,
            },
        },
        "shared_contexts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "anchor": {"type": "string"},
                    "scope": {
                        "type": "string",
                        "enum": [
                            "section_instruction",
                            "shared_passage",
                            "word_bank",
                            "exam_metadata",
                            "other",
                        ],
                    },
                    "owner": {"type": "string"},
                    "governs": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["anchor", "scope", "owner", "governs"],
                "additionalProperties": False,
            },
        },
        "other_anchors": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["title_anchors", "questions", "shared_contexts", "other_anchors"],
    "additionalProperties": False,
}


async def grouping_a(
    client: OpenAIClient, label: str, chunks: tuple[DocxChunk, ...], effort: str = "low"
) -> MethodResult:
    record = await client.responses(
        label=label,
        model=GROUPING_MODEL,
        instructions=GROUPING_INSTRUCTIONS,
        user_text=render_chunks(chunks),
        schema_name="exam_source_manifest",
        schema=GROUPING_SCHEMA,
        reasoning_effort=effort,
        max_output_tokens=60_000,
    )
    output = responses_output_json(record) if record.ok else None
    grouping = _grouping_from_manifest(output, chunks) if output else None
    return MethodResult([record], grouping)


def _grouping_from_manifest(manifest: dict[str, Any], chunks: tuple[DocxChunk, ...]) -> Grouping:
    known = {chunk.anchor for chunk in chunks}
    invalid: list[str] = []

    def valid(anchors: list[str]) -> list[str]:
        invalid.extend(anchor for anchor in anchors if anchor not in known)
        return [anchor for anchor in anchors if anchor in known]

    questions = [
        Question(
            id=entry["id"],
            anchors=valid(entry["anchors"]),
            key_anchors=valid(entry["answer_key_anchors"]),
            subpart_anchors=valid(entry["subpart_anchors"]),
        )
        for entry in manifest["questions"]
    ]
    contexts = [
        Context(
            anchor=entry["anchor"],
            scope=entry["scope"],
            owner=entry["owner"],
            governs=entry["governs"],
        )
        for entry in manifest["shared_contexts"]
        if valid([entry["anchor"]])
    ]
    return Grouping(
        method="grouping_a",
        questions=questions,
        contexts=contexts,
        title=valid(manifest["title_anchors"]),
        other=valid(manifest["other_anchors"]),
        invalid_anchors=invalid,
    )


# Grouping B: Decisions chunk roles, then code builds the groups.


def _role_instructions(chunks: tuple[DocxChunk, ...], index: int, *, quote_chunks: bool) -> str:
    chunk = chunks[index]
    asked = (
        f"Which structural role does source chunk [{chunk.anchor}] play in the exam? "
        "Judge layout, numbering and instructions, not subject matter."
    )
    if not quote_chunks:
        return asked
    previous = chunks[index - 1].marked_text if index else "(start of exam)"
    return f"{asked}\nThe chunk reads: {chunk.marked_text}\nThe chunk before it reads: {previous}"


async def grouping_b(
    client: OpenAIClient, label: str, chunks: tuple[DocxChunk, ...], *, quote_chunks: bool = False
) -> MethodResult:
    """Decisions-only grouping; quote_chunks repeats each chunk and its predecessor in its question."""
    text = render_chunks(chunks)
    role_questions = [
        {
            "type": "choice",
            "name": f"role_{_short(chunk.anchor)}",
            "instructions": _role_instructions(chunks, index, quote_chunks=quote_chunks),
            "choices": _choices(ROLE_LABELS),
        }
        for index, chunk in enumerate(chunks)
    ]
    role_calls, role_answers = await decide(client, f"{label}-roles", text, role_questions)
    roles = {
        chunk.anchor: role_answers.get(f"role_{_short(chunk.anchor)}", {}).get("choice", "other")
        for chunk in chunks
    }
    shared = [chunk.anchor for chunk in chunks if roles[chunk.anchor] == "shared_context"]
    scope_calls: list[CallRecord] = []
    scopes: dict[str, str] = {}
    if shared:
        scope_questions = [
            {
                "type": "choice",
                "name": f"scope_{_short(anchor)}",
                "instructions": f"Which questions does the shared context in chunk [{anchor}] govern?",
                "choices": _choices(SCOPE_LABELS),
            }
            for anchor in shared
        ]
        scope_calls, scope_answers = await decide(client, f"{label}-scope", text, scope_questions)
        scopes = {
            anchor: scope_answers.get(f"scope_{_short(anchor)}", {}).get("choice", "following_run")
            for anchor in shared
        }
    grouping = build_grouping_from_roles(chunks, roles, scopes)
    return MethodResult(
        role_calls + scope_calls,
        {"grouping": grouping, "roles": roles, "scopes": scopes, "answers": role_answers},
    )


def build_grouping_from_roles(
    chunks: tuple[DocxChunk, ...], roles: dict[str, str], scopes: dict[str, str]
) -> Grouping:
    questions: list[Question] = []
    title: list[str] = []
    other: list[str] = []
    pending: list[tuple[str, int]] = []  # shared anchor and index of the first question after it
    boundaries: list[
        int
    ] = []  # question index at each section break (shared context or other heading)
    for chunk in chunks:
        role = roles[chunk.anchor]
        if role == "title":
            title.append(chunk.anchor)
        elif role == "question_start" or (
            role in {"question_content", "subpart"} and not questions
        ):
            questions.append(Question(id=f"q{len(questions) + 1}", anchors=[chunk.anchor]))
        elif role in {"question_content", "subpart"}:
            questions[-1].anchors.append(chunk.anchor)
            if role == "subpart":
                questions[-1].subpart_anchors.append(chunk.anchor)
        elif role == "answer_key" and questions:
            questions[-1].key_anchors.append(chunk.anchor)
        elif role == "shared_context":
            pending.append((chunk.anchor, len(questions)))
            boundaries.append(len(questions))
        else:
            other.append(chunk.anchor)
    contexts = []
    for anchor, first in pending:
        scope = scopes.get(anchor, "following_run")
        if scope == "whole_exam":
            governed = range(len(questions))
        elif scope == "next_question":
            governed = range(first, min(first + 1, len(questions)))
        else:
            end = min([b for b in boundaries if b > first] + [len(questions)])
            governed = range(first, end)
        contexts.append(Context(anchor, scope, "exam", [questions[i].id for i in governed]))
    return Grouping("grouping_b", questions, contexts, title, other)


# Per-question labeling over a grouping.


def render_questions(
    grouping: Grouping, chunks: tuple[DocxChunk, ...], *, line_ids: bool = False
) -> str:
    text = {chunk.anchor: chunk.marked_text for chunk in chunks}
    blocks = []
    for question in grouping.questions:
        lines = [f"### Question {question.id}"]
        governing = [c.anchor for c in grouping.contexts if question.id in c.governs]
        if governing:
            lines.append("Governing context:")
            lines += [f"[{anchor}] {text[anchor]}" for anchor in governing]
        lines.append("Source:")
        for anchor in question.anchors:
            if line_ids:
                for number, line in enumerate(text[anchor].split("\n"), start=1):
                    lines.append(f"[{anchor}#{number}] {line}")
            else:
                lines.append(f"[{anchor}] {text[anchor]}")
        lines += [f"[{anchor}] (answer key) {text[anchor]}" for anchor in question.key_anchors]
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks)


def kind_questions(grouping: Grouping) -> list[dict[str, Any]]:
    return [
        {
            "type": "choice",
            "name": f"kind_{question.id}",
            "instructions": f"Which response action does question {question.id} ask the student to perform? "
            "Judge its stem, options, subparts and governing context together as one question. "
            "Answer-key lines show keyed answers; they do not change the requested response action.",
            "choices": _choices(KIND_LABELS),
        }
        for question in grouping.questions
    ]


async def kind(
    client: OpenAIClient, label: str, grouping: Grouping, chunks: tuple[DocxChunk, ...]
) -> MethodResult:
    calls, answers = await decide(
        client, label, render_questions(grouping, chunks), kind_questions(grouping)
    )
    return MethodResult(calls, answers)


async def kind_with_images(
    client: OpenAIClient,
    label: str,
    grouping: Grouping,
    chunks: tuple[DocxChunk, ...],
    images: list[str],
) -> MethodResult:
    content: list[dict[str, Any]] = [
        {"type": "input_text", "text": render_questions(grouping, chunks)}
    ]
    content += [{"type": "input_image", "image_url": image} for image in images]
    calls, answers = await decide(
        client, label, [{"role": "user", "content": content}], kind_questions(grouping)
    )
    return MethodResult(calls, answers)


async def ambiguity(
    client: OpenAIClient, label: str, grouping: Grouping, chunks: tuple[DocxChunk, ...]
) -> MethodResult:
    questions = [
        {
            "type": "score",
            "name": f"ambiguity_{question.id}",
            "instructions": f"How ambiguous are the response action and the source scope of question {question.id}?",
            "levels": [
                {"label": "clear", "description": "One response action and one scope are evident."},
                {
                    "label": "some_doubt",
                    "description": "The likely reading is clear but another is possible.",
                },
                {
                    "label": "ambiguous",
                    "description": "Several response actions or scopes are plausible.",
                },
            ],
        }
        for question in grouping.questions
    ]
    calls, answers = await decide(client, label, render_questions(grouping, chunks), questions)
    return MethodResult(calls, answers)


def answer_lines(grouping: Grouping, chunks: tuple[DocxChunk, ...]) -> list[str]:
    text = {chunk.anchor: chunk.marked_text for chunk in chunks}
    return [
        f"{anchor}#{number}"
        for question in grouping.questions
        for anchor in question.anchors
        for number, line in enumerate(text[anchor].split("\n"), start=1)
        if line.strip()
    ]


async def answer_slots(
    client: OpenAIClient, label: str, grouping: Grouping, chunks: tuple[DocxChunk, ...]
) -> MethodResult:
    lines = answer_lines(grouping, chunks)
    questions = [
        {
            "type": "predicate",
            "name": f"slot_{line.replace('body:', '').replace('#', '_')}",
            "instructions": f"Line [{line}] contains a field the student fills in (a blank, answer line or "
            "position to write an answer), as opposed to given text, listed options or instructions. "
            "Text marked <i>...</i> inside a sentence can be a key answer printed in a student field.",
        }
        for line in lines
    ]
    calls, answers = await decide(
        client, label, render_questions(grouping, chunks, line_ids=True), questions
    )
    return MethodResult(calls, {"lines": lines, "answers": answers})


# Placements.


def render_marked_document(grouping: Grouping, chunks: tuple[DocxChunk, ...]) -> str:
    owner = {anchor: question.id for question in grouping.questions for anchor in question.anchors}
    lines = []
    for chunk in chunks:
        mark = f" <{owner[chunk.anchor]}>" if chunk.anchor in owner else ""
        lines.append(f"[{chunk.anchor}]{mark} {chunk.marked_text}")
    return "\n".join(lines)


def _first_position(grouping: Grouping, chunks: tuple[DocxChunk, ...]) -> dict[str, int]:
    order = {chunk.anchor: index for index, chunk in enumerate(chunks)}
    return {q.id: min((order[a] for a in q.anchors), default=10**9) for q in grouping.questions}


async def facit_attachment(
    client: OpenAIClient, label: str, grouping: Grouping, chunks: tuple[DocxChunk, ...]
) -> MethodResult:
    order = {chunk.anchor: index for index, chunk in enumerate(chunks)}
    starts = _first_position(grouping, chunks)
    ranked = sorted(grouping.questions, key=lambda q: starts[q.id])
    keys = sorted({a for q in grouping.questions for a in q.key_anchors}, key=order.__getitem__)
    questions = []
    for anchor in keys:
        before = [q.id for q in ranked if starts[q.id] < order[anchor]][-5:]
        after = [q.id for q in ranked if starts[q.id] > order[anchor]][:2]
        candidates = before + after
        if not candidates:
            continue
        questions.append(
            {
                "type": "choice",
                "name": f"facit_{_short(anchor)}",
                "instructions": f"Chunk [{anchor}] is answer-key material. Which question, marked <q...> "
                "on its source lines, does it give the answer for?",
                "choices": [{"value": qid, "description": f"Question {qid}."} for qid in candidates]
                + [{"value": "none", "description": "None of these questions."}],
            }
        )
    calls, answers = await decide(
        client, label, render_marked_document(grouping, chunks), questions
    )
    return MethodResult(calls, {"keys": keys, "answers": answers})


async def points(
    client: OpenAIClient, label: str, grouping: Grouping, chunks: tuple[DocxChunk, ...]
) -> MethodResult:
    questions = [
        {
            "type": "choice",
            "name": f"points_{question.id}",
            "instructions": f"How many points is question {question.id} (lines marked <{question.id}>) worth? "
            "Use the value printed for that question. When no value is printed for it but a printed total "
            "covers a group of questions that includes it, use its equal share of that total. "
            "Choose unknown when the source states neither.",
            "choices": [
                {
                    "value": value,
                    "description": f"{value} points" if value != "unknown" else "Not stated.",
                }
                for value in POINT_VALUES
            ],
        }
        for question in grouping.questions
    ]
    calls, answers = await decide(
        client, label, render_marked_document(grouping, chunks), questions
    )
    return MethodResult(calls, answers)


def dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False)
