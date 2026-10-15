"""Provider-facing labeling methods. Inputs are source chunks and model output only; never gold."""

from __future__ import annotations

from typing import Any

from scripts.labeling_feasibility.api import OpenAIClient
from scripts.labeling_feasibility.method_models import Grouping
from scripts.labeling_feasibility.requests import MethodResult, decide
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk

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


def _choices(labels: tuple[tuple[str, str], ...]) -> list[dict[str, str]]:
    return [{"value": value, "description": description} for value, description in labels]


def _short(anchor: str) -> str:
    return anchor.replace("body:", "")


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
