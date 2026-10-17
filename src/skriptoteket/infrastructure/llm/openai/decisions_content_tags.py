"""Central-content Decisions request and response contract (TASK-SKRIPT-39-08-03).

Transport, retries and the provider model remain owned by decisions_item_labeler.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from pydantic import JsonValue

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    SourceImage,
    input_content,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_content_tags import ExamContentItem
from skriptoteket.protocols.item_type_labeler import (
    ContentTagChoice,
    ItemTypeLabelerError,
    LabelingItem,
)

_JsonObject = dict[str, JsonValue]


def _question_id(index: int) -> str:
    return f"q{index + 1}"


def build_content_decisions_payload(
    items: Sequence[LabelingItem], content_items: Sequence[ExamContentItem], *, model: str
) -> _JsonObject:
    """One closed choice per question; short wire IDs preserve arbitrary snapshot text."""
    text = "Choose the central-content item this question assesses, or none."
    images: list[SourceImage] = []
    for index, item in enumerate(items):
        text += f"\n\n### Question {_question_id(index)}\n"
        images.extend(SourceImage(image.png, len(text) + image.offset) for image in item.images)
        text += item.source_text
    choices: list[JsonValue] = [
        {"value": f"c{index}", "description": item.text} for index, item in enumerate(content_items)
    ]
    choices.append({"value": "none", "description": "Inget av dessa"})
    questions: list[JsonValue] = [
        {
            "type": "choice",
            "name": f"content_{_question_id(index)}",
            "instructions": (
                f"Which central-content item does question {_question_id(index)} assess?"
            ),
            "choices": choices,
        }
        for index in range(len(items))
    ]
    source: JsonValue = (
        [{"role": "user", "content": input_content(text, tuple(images))}] if images else text
    )
    return {"model": model, "input": source, "questions": questions}


def parse_content_decisions_answers(
    body: JsonValue, items: Sequence[LabelingItem], content_items: Sequence[ExamContentItem]
) -> tuple[list[ContentTagChoice], int | None]:
    """Reject incomplete or misidentified answers instead of inventing citations."""
    listed = body.get("answers") if isinstance(body, dict) else None
    if not isinstance(body, dict) or not isinstance(listed, list):
        raise _malformed("Content response has no answers list.")
    answers: dict[str, _JsonObject] = {}
    for answer in listed:
        if not isinstance(answer, dict) or not isinstance(answer.get("name"), str):
            raise _malformed("Content answer has no name.")
        name = str(answer["name"])
        if name in answers:
            raise _malformed("Content question answered twice.")
        answers[name] = answer
    expected = {f"content_{_question_id(index)}": item for index, item in enumerate(items)}
    if set(answers) != set(expected):
        raise _malformed("Content answers do not match the questions.")
    allowed: dict[str, str | None] = {
        f"c{index}": item.id for index, item in enumerate(content_items)
    }
    allowed["none"] = None
    results: list[ContentTagChoice] = []
    for name, item in expected.items():
        answer = answers[name]
        if answer.get("type") == "refusal":
            results.append(ContentTagChoice(item.item_id, None, 0.0))
            continue
        listed_probabilities = answer.get("probabilities")
        if answer.get("type") != "choice" or not isinstance(listed_probabilities, list):
            raise _malformed("Content answer is not a choice with probabilities.")
        probabilities: dict[str, float] = {}
        for entry in listed_probabilities:
            if not isinstance(entry, dict):
                raise _malformed("Content probability entry is not an object.")
            value, probability = entry.get("value"), entry.get("probability")
            if (
                not isinstance(value, str)
                or value not in allowed
                or value in probabilities
                or isinstance(probability, bool)
                or not isinstance(probability, int | float)
                or not math.isfinite(probability)
                or not 0 <= probability <= 1
            ):
                raise _malformed("Content probability or choice is invalid.")
            probabilities[value] = float(probability)
        choice = answer.get("choice")
        if (
            set(probabilities) != set(allowed)
            or not isinstance(choice, str)
            or choice not in allowed
        ):
            raise _malformed("Content probabilities do not cover the closed choice set.")
        if probabilities[choice] != max(probabilities.values()):
            raise _malformed("Content choice is not the top probability.")
        results.append(ContentTagChoice(item.item_id, allowed[choice], probabilities[choice]))
    usage = body.get("usage")
    tokens = usage.get("input_tokens") if isinstance(usage, dict) else None
    input_tokens = tokens if isinstance(tokens, int) and not isinstance(tokens, bool) else None
    return results, input_tokens


def _malformed(message: str) -> ItemTypeLabelerError:
    return ItemTypeLabelerError(code="malformed_response", message=message)
