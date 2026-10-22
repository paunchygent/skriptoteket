from __future__ import annotations

from collections.abc import Callable
from functools import partial

import pytest

from skriptoteket.infrastructure.llm.openai.decisions_item_labeler import (
    OpenAIDecisionsItemTypeLabeler,
)
from skriptoteket.protocols.item_type_labeler import (
    LabelRoute,
)
from tests.unit.infrastructure.llm.decisions_item_labeler_support import (
    ACCEPT_BOUNDARY,
    CORPUS_24,
    Harness,
    RecordingSleeper,
    chosen_probability,
    escalated_answers,
    load,
    replay,
    request_for,
)
from tests.unit.llm_door_fakes import RecordingDoor

pytestmark = pytest.mark.unit


async def test_environment_cannot_move_the_decided_threshold_or_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The first pass keeps the 0.95 boundary and its model whatever the environment says."""
    monkeypatch.setenv("LLM_ITEM_LABELER_ACCEPT_THRESHOLD", "0.5")
    monkeypatch.setenv("LLM_ITEM_LABELER_MODEL", "another-model")
    fixture = load(CORPUS_24)
    harness = Harness(replay(fixture["exchanges"]))
    labeler = OpenAIDecisionsItemTypeLabeler(
        door=harness.door,
        timeout_seconds=30,
        sleeper=harness.sleeper,
    )

    labeling = await labeler.label(request=request_for(fixture))

    assert {sent["model"] for sent in harness.requests} == {"gpt-6-luna"}
    assert all(r.threshold == ACCEPT_BOUNDARY for r in labeling.results)
    # A 0.5 boundary would accept answers in [0.5, 0.95); the decided 0.95 escalates them.
    answers = load(CORPUS_24)["exchanges"][0]["body"]["answers"]
    assert any(0.5 <= chosen_probability(a) < ACCEPT_BOUNDARY for a in answers)
    escalated = [r for r in labeling.results if r.route == LabelRoute.ESCALATE]
    assert len(escalated) == len(escalated_answers(fixture))
    assert all(r.probability < ACCEPT_BOUNDARY for r in escalated)
    assert len(harness.requests) == 1


def _labeler(
    *, timeout_seconds: float = 30, max_attempts: int = 3
) -> OpenAIDecisionsItemTypeLabeler:
    async def _unused(sent):  # pragma: no cover
        raise AssertionError("construction must not call the door")

    return OpenAIDecisionsItemTypeLabeler(
        door=RecordingDoor(_unused),
        timeout_seconds=timeout_seconds,
        sleeper=RecordingSleeper(),
        max_attempts=max_attempts,
    )


@pytest.mark.parametrize(
    "build",
    [
        pytest.param(partial(_labeler, timeout_seconds=0), id="zero_timeout"),
        pytest.param(partial(_labeler, max_attempts=0), id="zero_attempts"),
    ],
)
def test_invalid_configuration_is_rejected_at_construction(
    build: Callable[[], OpenAIDecisionsItemTypeLabeler],
) -> None:
    with pytest.raises(ValueError):
        build()
