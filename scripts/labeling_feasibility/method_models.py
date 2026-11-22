"""Saved grouping structure shared by the provider grouping methods."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypedDict

from pydantic import JsonValue


class GroupingBOutput(TypedDict, total=False):
    """The saved output of a grouping_b method file; readers use only the grouping."""

    grouping: JsonValue


def grouping_b_output(value: JsonValue) -> GroupingBOutput:
    if not isinstance(value, dict):
        raise TypeError("grouping_b output must be a JSON object")
    output: GroupingBOutput = {}
    if "grouping" in value:
        output["grouping"] = value["grouping"]
    return output


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


def _json_str(value: JsonValue, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"grouping {field_name} must be a string")
    return value


def _json_str_list(value: JsonValue, field_name: str) -> list[str]:
    if not isinstance(value, list):
        raise TypeError(f"grouping {field_name} must be a JSON array")
    return [_json_str(item, field_name) for item in value]


def _json_list(value: JsonValue, field_name: str) -> list[JsonValue]:
    if not isinstance(value, list):
        raise TypeError(f"grouping {field_name} must be a JSON array")
    return list(value)


def _question_from_json(value: JsonValue) -> Question:
    if not isinstance(value, dict):
        raise TypeError("grouping questions must be JSON objects")
    unknown = set(value) - {"id", "anchors", "key_anchors", "subpart_anchors"}
    if unknown:
        raise TypeError(f"unexpected grouping question fields: {sorted(unknown)}")
    return Question(
        id=_json_str(value["id"], "question id"),
        anchors=_json_str_list(value["anchors"], "question anchors"),
        key_anchors=_json_str_list(value.get("key_anchors", []), "question key_anchors"),
        subpart_anchors=_json_str_list(
            value.get("subpart_anchors", []), "question subpart_anchors"
        ),
    )


def _context_from_json(value: JsonValue) -> Context:
    if not isinstance(value, dict):
        raise TypeError("grouping contexts must be JSON objects")
    unknown = set(value) - {"anchor", "scope", "owner", "governs"}
    if unknown:
        raise TypeError(f"unexpected grouping context fields: {sorted(unknown)}")
    return Context(
        anchor=_json_str(value["anchor"], "context anchor"),
        scope=_json_str(value["scope"], "context scope"),
        owner=_json_str(value["owner"], "context owner"),
        governs=_json_str_list(value["governs"], "context governs"),
    )


def _question_json(question: Question) -> dict[str, JsonValue]:
    anchors: list[JsonValue] = [anchor for anchor in question.anchors]
    key_anchors: list[JsonValue] = [anchor for anchor in question.key_anchors]
    subpart_anchors: list[JsonValue] = [anchor for anchor in question.subpart_anchors]
    return {
        "id": question.id,
        "anchors": anchors,
        "key_anchors": key_anchors,
        "subpart_anchors": subpart_anchors,
    }


def _context_json(context: Context) -> dict[str, JsonValue]:
    governs: list[JsonValue] = [qid for qid in context.governs]
    return {
        "anchor": context.anchor,
        "scope": context.scope,
        "owner": context.owner,
        "governs": governs,
    }


@dataclass
class Grouping:
    method: str
    questions: list[Question]
    contexts: list[Context]
    title: list[str]
    other: list[str]
    invalid_anchors: list[JsonValue] = field(default_factory=list)

    def to_json(self) -> dict[str, JsonValue]:
        questions: list[JsonValue] = [_question_json(question) for question in self.questions]
        contexts: list[JsonValue] = [_context_json(context) for context in self.contexts]
        title: list[JsonValue] = [anchor for anchor in self.title]
        other: list[JsonValue] = [anchor for anchor in self.other]
        return {
            "method": self.method,
            "questions": questions,
            "contexts": contexts,
            "title": title,
            "other": other,
            "invalid_anchors": self.invalid_anchors,
        }

    @classmethod
    def from_json(cls, saved: JsonValue) -> Grouping:
        if not isinstance(saved, dict):
            raise TypeError("grouping must be a JSON object")
        questions = saved["questions"]
        contexts = saved["contexts"]
        if not isinstance(questions, list) or not isinstance(contexts, list):
            raise TypeError("grouping questions and contexts must be JSON arrays")
        return cls(
            method=_json_str(saved["method"], "method"),
            questions=[_question_from_json(question) for question in questions],
            contexts=[_context_from_json(context) for context in contexts],
            title=_json_str_list(saved["title"], "title"),
            other=_json_str_list(saved["other"], "other"),
            invalid_anchors=_json_list(saved["invalid_anchors"], "invalid_anchors"),
        )
