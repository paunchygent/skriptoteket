from __future__ import annotations

import copy
import json
from collections.abc import Callable

import pytest

from skriptoteket.infrastructure.llm.openai.decisions_item_labeler import (
    parse_decisions_answers,
)
from skriptoteket.protocols.item_type_labeler import (
    ACCEPT_THRESHOLD,
    ItemTypeLabel,
    ItemTypeLabelerError,
    ItemTypeLabeling,
    LabelRoute,
)
from tests.unit.infrastructure.llm.decisions_item_labeler_support import (
    CORPUS_24,
    Answer,
    Body,
    Harness,
    Responder,
    chosen_probability,
    escalated_answers,
    load,
    replay,
    request_for,
    with_mutated_body,
)

pytestmark = pytest.mark.unit


async def _label_24(responder: Responder) -> ItemTypeLabeling:
    harness = Harness(responder)
    return await harness.labeler().label(request=request_for(load(CORPUS_24)))


async def _expect_error(responder: Responder) -> ItemTypeLabelerError:
    with pytest.raises(ItemTypeLabelerError) as caught:
        await _label_24(responder)
    return caught.value


def _recorded_answers_24() -> list[Answer]:
    return load(CORPUS_24)["exchanges"][0]["body"]["answers"]


def test_threshold_routes_recorded_answers_at_the_095_boundary() -> None:
    fixture = load(CORPUS_24)

    body = json.loads(json.dumps(fixture["exchanges"][0]["body"]))
    results, _ = parse_decisions_answers(body, request_for(fixture).items)

    answers = _recorded_answers_24()
    probabilities = [chosen_probability(answer) for answer in answers]
    assert any(p == 0.95 for p in probabilities)
    assert any(0.94 <= p < 0.95 for p in probabilities)
    assert len(results) == len(answers) == len(fixture["items"])
    for result, answer, item in zip(results, answers, fixture["items"], strict=True):
        probability = chosen_probability(answer)
        assert result.item_id == item["item_id"]
        assert result.label == ItemTypeLabel(answer["choice"])
        assert result.probability == probability
        assert result.threshold == 0.95
        expected = LabelRoute.ACCEPT if probability >= 0.95 else LabelRoute.ESCALATE
        assert result.route == expected
    assert any(r.probability == 0.95 and r.route == LabelRoute.ACCEPT for r in results)
    assert any(r.probability < 0.95 and r.route == LabelRoute.ESCALATE for r in results)


async def test_public_label_escalates_exactly_the_answers_below_the_boundary() -> None:
    fixture = load(CORPUS_24)
    harness = Harness(replay(fixture["exchanges"]))

    labeling = await harness.labeler().label(request=request_for(fixture))

    answers = _recorded_answers_24()
    for result, answer in zip(labeling.results, answers, strict=True):
        probability = chosen_probability(answer)
        assert result.label == ItemTypeLabel(answer["choice"])
        assert result.probability == probability
        assert result.first_pass is None
        expected = LabelRoute.ACCEPT if probability >= ACCEPT_THRESHOLD else LabelRoute.ESCALATE
        assert result.route == expected
    assert sum(r.route is LabelRoute.ESCALATE for r in labeling.results) == len(
        escalated_answers(fixture)
    )
    assert len(harness.requests) == 1


def _replace_choice(body: Body) -> None:
    body["answers"][0]["choice"] = "essay"


def _replace_probability_value(body: Body) -> None:
    body["answers"][0]["probabilities"][1]["value"] = "essay"


def _remove_answer(body: Body) -> None:
    del body["answers"][3]


def _duplicate_answer(body: Body) -> None:
    body["answers"].append(copy.deepcopy(body["answers"][3]))


def _remove_answers_key(body: Body) -> None:
    del body["answers"]


def _probability_above_one(body: Body) -> None:
    body["answers"][0]["probabilities"][0]["probability"] = 1.5


@pytest.mark.parametrize(
    ("mutate", "code"),
    [
        (_replace_choice, "unknown_label"),
        (_replace_probability_value, "unknown_label"),
        (_remove_answer, "malformed_response"),
        (_duplicate_answer, "malformed_response"),
        (_remove_answers_key, "malformed_response"),
        (_probability_above_one, "malformed_response"),
    ],
)
async def test_mutated_recorded_body_is_rejected(mutate: Callable[[Body], None], code: str) -> None:
    error = await _expect_error(with_mutated_body(mutate))

    assert error.code == code


async def test_refusal_escalates_only_the_refused_item() -> None:
    fixture = load(CORPUS_24)
    baseline = await _label_24(replay(fixture["exchanges"]))
    refused_index = 2

    def refuse(body: Body) -> None:
        name = body["answers"][refused_index]["name"]
        body["answers"][refused_index] = {"type": "refusal", "name": name}

    labeling = await _label_24(with_mutated_body(refuse))

    refused = labeling.results[refused_index]
    assert refused.item_id == fixture["items"][refused_index]["item_id"]
    assert refused.label == ItemTypeLabel.UNRESOLVED
    assert refused.route == LabelRoute.ESCALATE
    assert refused.refused is True
    assert dict(refused.probabilities) == {}
    assert refused.first_pass is None
    others = [r for i, r in enumerate(labeling.results) if i != refused_index]
    expected = [r for i, r in enumerate(baseline.results) if i != refused_index]
    assert others == expected
