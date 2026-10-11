from __future__ import annotations

import httpx
import pytest
from dishka import Provider, Scope, from_context, make_async_container

from skriptoteket.config import Settings
from skriptoteket.di.item_type_labeler import ItemTypeLabelerProvider
from skriptoteket.protocols.item_type_labeler import (
    ItemTypeLabelerError,
    LabelRoute,
    MeteredItemTypeLabelerProtocol,
)
from skriptoteket.protocols.sleeper import SleeperProtocol
from tests.unit.infrastructure.llm.decisions_item_labeler_support import (
    ACCEPT_BOUNDARY,
    CORPUS_24,
    Harness,
    chosen_probability,
    escalated_answers,
    load,
    replay,
    request_for,
)

pytestmark = pytest.mark.unit


class _LabelerInputs(Provider):
    client = from_context(provides=httpx.AsyncClient, scope=Scope.APP)
    sleeper = from_context(provides=SleeperProtocol, scope=Scope.APP)
    settings = from_context(provides=Settings, scope=Scope.APP)


async def test_environment_cannot_move_the_decided_threshold_or_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The wired labeler keeps the 0.95 boundary and its model whatever the environment says."""
    monkeypatch.setenv("LLM_ITEM_LABELER_ACCEPT_THRESHOLD", "0.5")
    monkeypatch.setenv("LLM_ITEM_LABELER_MODEL", "another-model")
    settings = Settings(
        _env_file=None,
        LLM_ANSWER_KEY_BASE_URL="https://example.test",
        OPENAI_LLM_ANSWER_KEY_API_KEY="fixture-key",
    )
    fixture = load(CORPUS_24)
    harness = Harness(replay(fixture["exchanges"]))
    container = make_async_container(
        ItemTypeLabelerProvider(),
        _LabelerInputs(),
        context={
            httpx.AsyncClient: httpx.AsyncClient(transport=httpx.MockTransport(harness.handle)),
            SleeperProtocol: harness.sleeper,
            Settings: settings,
        },
        # The leased request-scope labeler needs a database; only the adapter is wired here.
        skip_validation=True,
    )
    labeler = await container.get(MeteredItemTypeLabelerProtocol)

    labeling = await labeler.label(request=request_for(fixture))
    await container.close()

    assert {sent["model"] for sent in harness.requests} == {"gpt-6-luna"}
    assert all(r.threshold == ACCEPT_BOUNDARY for r in labeling.results)
    below = [r.first_pass for r in labeling.results if r.first_pass is not None]
    assert below
    assert all(first.route == LabelRoute.ESCALATE and first.probability < 0.95 for first in below)
    # A 0.5 boundary would re-ask only answers below it; the decided 0.95 re-asks every one below.
    answers = load(CORPUS_24)["exchanges"][0]["body"]["answers"]
    assert any(0.5 <= chosen_probability(a) < ACCEPT_BOUNDARY for a in answers)
    assert len(below) == len(escalated_answers(fixture))
    assert len(harness.requests) == 1 + len(below)


async def test_missing_api_key_fails_before_any_request() -> None:
    harness = Harness(replay(load(CORPUS_24)["exchanges"]))

    with pytest.raises(ItemTypeLabelerError) as caught:
        await harness.labeler(api_key="").label(request=request_for(load(CORPUS_24)))

    assert caught.value.code == "config_missing"
    assert harness.requests == []
