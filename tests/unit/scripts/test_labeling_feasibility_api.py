"""Provider replies are narrowed at the boundary without dropping saved evidence."""

from __future__ import annotations

import pytest
from pydantic import JsonValue

from scripts.labeling_feasibility.api import (
    CallRecord,
    decision_answers,
    responses_output_json,
)
from scripts.labeling_feasibility.requests import MethodResult, answers_json

pytestmark = pytest.mark.unit


def _record(endpoint: str, body: JsonValue) -> CallRecord:
    return CallRecord(endpoint, "label", 200, 0.1, {}, body)


def test_decision_answers_keep_every_field_of_each_answer_object() -> None:
    answer: dict[str, JsonValue] = {
        "name": "kind_q1",
        "type": "choice",
        "choice": "free_text",
        "extra_field": {"kept": [1, 2]},
    }
    record = _record("decisions", {"answers": [answer, "skipped", {"no_name": 1}]})

    answers = decision_answers(record)

    assert answers == {"kind_q1": answer}
    assert MethodResult([record], answers_json(answers)).output == {"kind_q1": answer}


def test_call_record_to_json_saves_the_usage_object_whole() -> None:
    usage: dict[str, JsonValue] = {
        "input_tokens": 10,
        "output_tokens": 2,
        "total_tokens": 12,
        "input_tokens_details": {"cached_tokens": 4, "audio_tokens": 1},
    }
    record = _record("responses", {"usage": usage})

    assert record.to_json()["usage"] == usage


def test_responses_output_json_parses_the_first_output_text_part() -> None:
    body: JsonValue = {
        "output": [
            "not an item",
            {"content": "not a list"},
            {"content": [{"type": "reasoning"}, {"type": "output_text", "text": '{"a": 1}'}]},
        ]
    }

    assert responses_output_json(_record("responses", body)) == {"a": 1}


def test_responses_output_json_is_none_without_text_or_output() -> None:
    assert responses_output_json(_record("responses", {"output": "x"})) is None
    assert (
        responses_output_json(
            _record("responses", {"output": [{"content": [{"type": "output_text"}]}]})
        )
        is None
    )
