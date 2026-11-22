"""Narrow shapes for the v14 batch recordings, limited to the fields the report reads."""

from __future__ import annotations

from typing import NotRequired, TypedDict

from pydantic import JsonValue


class ConvertedChoice(TypedDict):
    text: str
    correct: NotRequired[JsonValue]


class ConvertedSegment(TypedDict):
    kind: NotRequired[JsonValue]
    text: NotRequired[str]
    accepted_values: NotRequired[list[str]]


class ConvertedBodyRow(TypedDict):
    segments: NotRequired[list[ConvertedSegment]]


class ConvertedItem(TypedDict):
    source_anchors: list[str]
    kind: JsonValue
    points: NotRequired[int | float | str | None]
    choices: NotRequired[list[ConvertedChoice]]
    body: NotRequired[list[ConvertedBodyRow]]


class ConvertedInstruction(TypedDict):
    text: str


class ConvertedExam(TypedDict):
    items: list[ConvertedItem]
    instructions: NotRequired[list[ConvertedInstruction]]


def _str_field(value: JsonValue, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"converted {field_name} must be a string")
    return value


def _str_list(value: JsonValue, field_name: str) -> list[str]:
    if not isinstance(value, list):
        raise TypeError(f"converted {field_name} must be a JSON array")
    return [_str_field(item, field_name) for item in value]


def _anchor_list(value: JsonValue) -> list[str]:
    """Source anchors: non-strings were skipped by ``anchor in owner`` guards,
    except unhashable ones, where the guard itself raised TypeError."""
    if not isinstance(value, list):
        raise TypeError("converted source_anchors must be a JSON array")
    anchors: list[str] = []
    for anchor in value:
        if isinstance(anchor, str):
            anchors.append(anchor)
        else:
            hash(anchor)
    return anchors


def _converted_choice(value: JsonValue) -> ConvertedChoice:
    if not isinstance(value, dict):
        raise TypeError("converted choices must be JSON objects")
    choice: ConvertedChoice = {"text": _str_field(value["text"], "choice text")}
    if "correct" in value:
        choice["correct"] = value["correct"]
    return choice


def _converted_segment(value: JsonValue) -> ConvertedSegment:
    if not isinstance(value, dict):
        raise TypeError("converted body segments must be JSON objects")
    segment: ConvertedSegment = {}
    if "kind" in value:
        segment["kind"] = value["kind"]
    if "text" in value:
        segment["text"] = _str_field(value["text"], "segment text")
    if "accepted_values" in value:
        segment["accepted_values"] = _str_list(value["accepted_values"], "accepted_values")
    return segment


def _converted_body_row(value: JsonValue) -> ConvertedBodyRow:
    if not isinstance(value, dict):
        raise TypeError("converted body rows must be JSON objects")
    row: ConvertedBodyRow = {}
    if "segments" in value:
        segments = value["segments"]
        if not isinstance(segments, list):
            raise TypeError("converted body row segments must be a JSON array")
        row["segments"] = [_converted_segment(segment) for segment in segments]
    return row


def _converted_item(value: JsonValue) -> ConvertedItem:
    if not isinstance(value, dict):
        raise TypeError("converted items must be JSON objects")
    item: ConvertedItem = {
        "source_anchors": _anchor_list(value["source_anchors"]),
        "kind": value["kind"],
    }
    if "points" in value:
        points = value["points"]
        if points is not None and not isinstance(points, (int, float, str)):
            raise TypeError("converted item points must be a number or numeric string")
        item["points"] = points
    if "choices" in value:
        choices = value["choices"]
        if not isinstance(choices, list):
            raise TypeError("converted item choices must be a JSON array")
        item["choices"] = [_converted_choice(choice) for choice in choices]
    if "body" in value:
        body = value["body"]
        if not isinstance(body, list):
            raise TypeError("converted item body must be a JSON array")
        item["body"] = [_converted_body_row(row) for row in body]
    return item


def converted_exam(value: JsonValue) -> ConvertedExam:
    """Narrow a recorded batch conversion reply to the fields the package reads."""
    if not isinstance(value, dict):
        raise TypeError("converted exam recording must be a JSON object")
    items = value["items"]
    if not isinstance(items, list):
        raise TypeError("converted exam items must be a JSON array")
    exam: ConvertedExam = {"items": [_converted_item(item) for item in items]}
    if "instructions" in value:
        instructions = value["instructions"]
        if not isinstance(instructions, list):
            raise TypeError("converted exam instructions must be a JSON array")
        converted: list[ConvertedInstruction] = []
        for entry in instructions:
            if not isinstance(entry, dict):
                raise TypeError("converted exam instructions must be JSON objects")
            converted.append({"text": _str_field(entry["text"], "instruction text")})
        exam["instructions"] = converted
    return exam
