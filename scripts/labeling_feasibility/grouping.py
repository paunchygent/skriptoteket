"""Grouping methods: provider anchor manifests, or code-built roles and scopes."""

from __future__ import annotations

from typing import Any

from scripts.labeling_feasibility.api import (
    CallRecord,
    OpenAIClient,
    responses_output_json,
)
from scripts.labeling_feasibility.method_models import Context, Grouping, Question
from scripts.labeling_feasibility.requests import MethodResult, decide
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk

GROUPING_MODEL = "gpt-6-luna"

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


def render_chunks(chunks: tuple[DocxChunk, ...]) -> str:
    return "\n".join(f"[{chunk.anchor}] ({chunk.kind}) {chunk.marked_text}" for chunk in chunks)


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
