"""Two-pass item-type labeler (TASK-SKRIPT-39-05-04 D23).

The first pass is the real Decisions adapter replaying the recorded 24-question exchange
over ``httpx.MockTransport``; no live second-pass reply is recorded, so the second pass is a
scripted fake.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from skriptoteket.application.curated_apps.item_type_labeling import (
    TwoPassItemTypeLabeler,
)
from skriptoteket.protocols.item_type_labeler import (
    ACCEPT_THRESHOLD,
    ItemTypeLabel,
    ItemTypeLabelerError,
    ItemTypeLabelResult,
    LabelingItem,
    LabelingRequest,
    LabelPass,
    LabelRoute,
    SecondPassLabel,
)
from tests.unit.infrastructure.llm.decisions_item_labeler_support import (
    CORPUS_24,
    Body,
    Harness,
    always,
    load,
    replay,
    request_for,
    unavailable,
    with_mutated_body,
)

pytestmark = pytest.mark.unit

_B_PROFILE = "fake-second-pass"
_B_INPUT_TOKENS = 120
_B_OUTPUT_TOKENS = 9
_B_LABEL = ItemTypeLabel.GAP_FILL


class _FakeSecondPass:
    """Scripted pass B: a per-item outcome, otherwise a fixed label with measured usage."""

    provider_profile_id = _B_PROFILE

    def __init__(self, outcomes: dict[str, SecondPassLabel | ItemTypeLabelerError] | None = None):
        self.outcomes = outcomes or {}
        self.asked: list[str] = []

    def estimate_tokens(self, *, item: LabelingItem) -> int:
        return 4_000 + len(item.source_text)

    async def label_one(self, *, job_id: UUID, item: LabelingItem) -> SecondPassLabel:
        self.asked.append(item.item_id)
        outcome = self.outcomes.get(
            item.item_id, SecondPassLabel(_B_LABEL, _B_INPUT_TOKENS, _B_OUTPUT_TOKENS)
        )
        if isinstance(outcome, ItemTypeLabelerError):
            raise outcome
        return outcome


class _Setup:
    def __init__(
        self,
        first_pass_responder,
        second_pass: _FakeSecondPass | None = None,
    ) -> None:
        self.http = Harness(first_pass_responder)
        self.second = second_pass or _FakeSecondPass()
        self.first = self.http.labeler()
        self.labeler = TwoPassItemTypeLabeler(
            first_pass=self.first,
            second_pass=self.second,
        )
        self.sinks: list[tuple[ItemTypeLabelResult, ...]] = []

    async def label(self, request: LabelingRequest):
        return await self.labeler.label(request=request, on_results=self.sinks.append)


def _recorded() -> tuple[LabelingRequest, set[str]]:
    """The recorded exam and the ids whose recorded first-pass answer is below 0.95."""
    fixture = load(CORPUS_24)
    request = request_for(fixture)
    answers = fixture["exchanges"][0]["body"]["answers"]
    below = {
        item.item_id
        for item, answer in zip(request.items, answers, strict=True)
        if answer["type"] != "choice"
        or {e["value"]: e["probability"] for e in answer["probabilities"]}[answer["choice"]]
        < ACCEPT_THRESHOLD
    }
    return request, below


def _recorded_setup(second_pass: _FakeSecondPass | None = None) -> _Setup:
    return _Setup(replay(load(CORPUS_24)["exchanges"]), second_pass)


def _outage_setup() -> _Setup:
    return _Setup(always(unavailable(503)))


def _recorded_top(item_id: str) -> ItemTypeLabel:
    """The most probable label other than unresolved in the recorded first-pass answer."""
    request = request_for(load(CORPUS_24))
    answers = load(CORPUS_24)["exchanges"][0]["body"]["answers"]
    (answer,) = [
        a for item, a in zip(request.items, answers, strict=True) if item.item_id == item_id
    ]
    ranked = [e for e in answer["probabilities"] if e["value"] != ItemTypeLabel.UNRESOLVED]
    return ItemTypeLabel(max(ranked, key=lambda e: e["probability"])["value"])


async def test_first_pass_calls_the_network_and_reports_measured_tokens() -> None:
    request, _ = _recorded()
    setup = _recorded_setup()

    labeling = await setup.label(request)

    assert len(setup.http.requests) == 1
    recorded_tokens = load(CORPUS_24)["exchanges"][0]["body"]["usage"]["input_tokens"]
    assert labeling.usage.input_tokens is not None
    assert labeling.usage.input_tokens >= recorded_tokens


async def test_each_escalated_question_calls_the_second_pass_alone() -> None:
    request, below = _recorded()
    assert below
    setup = _recorded_setup()

    labeling = await setup.label(request)

    assert sorted(setup.second.asked) == sorted(below)
    recorded_tokens = load(CORPUS_24)["exchanges"][0]["body"]["usage"]["input_tokens"]
    assert labeling.usage.input_tokens == recorded_tokens + _B_INPUT_TOKENS * len(below)


async def test_second_pass_result_keeps_first_pass_probabilities_and_decides_alone() -> None:
    request, below = _recorded()
    setup = _recorded_setup()

    labeling = await setup.label(request)

    assert [r.item_id for r in labeling.results] == [i.item_id for i in request.items]
    for result in labeling.results:
        if result.item_id not in below:
            assert result.decided_by is LabelPass.FIRST
            assert result.first_pass is None
            assert result.route is LabelRoute.ACCEPT
            continue
        first = result.first_pass
        assert first is not None
        assert first.route is LabelRoute.ESCALATE
        assert first.probability < ACCEPT_THRESHOLD
        assert result.label is _B_LABEL
        assert result.route is LabelRoute.ACCEPT
        assert result.decided_by is LabelPass.SECOND
        assert result.failure_code is None
        assert dict(result.probabilities) == dict(first.probabilities)
        assert result.probability == first.probabilities.get(_B_LABEL, 0.0)


async def test_second_pass_failure_gives_one_question_its_first_pass_top_label() -> None:
    request, below = _recorded()
    failing = sorted(below)[0]
    setup = _recorded_setup(
        _FakeSecondPass(
            {failing: ItemTypeLabelerError(code="provider_unavailable", message="down")}
        )
    )

    labeling = await setup.label(request)

    assert len(labeling.results) == len(request.items)
    broken = next(r for r in labeling.results if r.item_id == failing)
    assert broken.label is _recorded_top(failing)
    assert broken.label is not ItemTypeLabel.UNRESOLVED
    assert broken.failure_code == "provider_unavailable"
    assert broken.decided_by is LabelPass.SECOND
    assert broken.first_pass is not None
    others = [r for r in labeling.results if r.item_id in below and r.item_id != failing]
    assert others
    assert all(r.label is _B_LABEL and r.failure_code is None for r in others)
    assert labeling.usage.input_tokens is None


async def test_unmeasured_second_pass_usage_still_returns_the_label() -> None:
    request, below = _recorded()
    unmeasured = sorted(below)[0]
    setup = _recorded_setup(
        _FakeSecondPass({unmeasured: SecondPassLabel(_B_LABEL, _B_INPUT_TOKENS, None)})
    )

    labeling = await setup.label(request)

    assert next(r for r in labeling.results if r.item_id == unmeasured).label is _B_LABEL


async def test_refused_second_pass_answer_is_carried_as_refused() -> None:
    request, below = _recorded()
    refused = sorted(below)[0]
    setup = _recorded_setup(
        _FakeSecondPass(
            {refused: SecondPassLabel(ItemTypeLabel.UNRESOLVED, _B_INPUT_TOKENS, 0, refused=True)}
        )
    )

    labeling = await setup.label(request)

    result = next(r for r in labeling.results if r.item_id == refused)
    assert result.refused is True
    assert result.label is _recorded_top(refused)
    assert result.failure_code is None


async def test_an_unresolved_second_pass_answer_converts_with_the_first_pass_top_label() -> None:
    request, below = _recorded()
    unresolved = sorted(below)[0]
    setup = _recorded_setup(
        _FakeSecondPass({unresolved: SecondPassLabel(ItemTypeLabel.UNRESOLVED, _B_INPUT_TOKENS, 0)})
    )

    labeling = await setup.label(request)

    result = next(r for r in labeling.results if r.item_id == unresolved)
    assert result.label is _recorded_top(unresolved)
    assert result.decided_by is LabelPass.SECOND
    assert result.probability == dict(result.probabilities)[result.label]
    assert result.probability < ACCEPT_THRESHOLD


async def test_a_first_pass_unresolved_label_above_the_threshold_goes_to_the_second_pass() -> None:
    request, below = _recorded()
    index, settled = next(
        (n, i.item_id) for n, i in enumerate(request.items) if i.item_id not in below
    )

    def unresolved_first(body: Body) -> None:
        answer = body["answers"][index]
        answer["choice"] = ItemTypeLabel.UNRESOLVED.value
        for entry in answer["probabilities"]:
            entry["probability"] = 0.97 if entry["value"] == "unresolved" else 0.005

    setup = _Setup(with_mutated_body(unresolved_first))

    labeling = await setup.label(request)

    assert settled in setup.second.asked
    result = next(r for r in labeling.results if r.item_id == settled)
    assert result.label is _B_LABEL
    assert result.decided_by is LabelPass.SECOND


async def test_on_results_receives_each_question_exactly_once_accepted_before_escalated() -> None:
    request, below = _recorded()
    setup = _recorded_setup()

    labeling = await setup.label(request)

    delivered = [result for batch in setup.sinks for result in batch]
    assert sorted(r.item_id for r in delivered) == sorted(i.item_id for i in request.items)
    accepted_batch = setup.sinks[0]
    assert {r.item_id for r in accepted_batch} == {i.item_id for i in request.items} - below
    assert all(r.decided_by is LabelPass.FIRST for r in accepted_batch)
    later = [r for batch in setup.sinks[1:] for r in batch]
    assert {r.item_id for r in later} == below
    assert all(
        len(batch) == 1 and batch[0].decided_by is LabelPass.SECOND for batch in setup.sinks[1:]
    )
    returned = {r.item_id: r for r in labeling.results}
    assert all(returned[r.item_id] == r for r in delivered)


async def test_failed_first_pass_sends_every_question_to_the_second_pass() -> None:
    request, _ = _recorded()
    setup = _outage_setup()

    labeling = await setup.label(request)

    assert len(setup.http.requests) == 3
    assert sorted(setup.second.asked) == sorted(i.item_id for i in request.items)
    for result in labeling.results:
        assert result.label is _B_LABEL
        assert result.decided_by is LabelPass.SECOND
        assert result.probability == 0.0
        assert result.first_pass is not None
        assert result.first_pass.failure_code == "provider_unavailable"
        assert result.first_pass.route is LabelRoute.ESCALATE
    delivered = [r for batch in setup.sinks for r in batch]
    assert sorted(r.item_id for r in delivered) == sorted(i.item_id for i in request.items)
    assert labeling.usage.input_tokens is None


async def test_failed_first_pass_with_failing_second_pass_leaves_every_question_without_label() -> (
    None
):
    request, _ = _recorded()
    error = ItemTypeLabelerError(code="provider_unavailable", message="down")
    setup = _Setup(
        always(unavailable(503)),
        _FakeSecondPass({item.item_id: error for item in request.items}),
    )

    labeling = await setup.label(request)

    assert [r.label for r in labeling.results] == [ItemTypeLabel.UNRESOLVED] * len(request.items)
    assert {r.failure_code for r in labeling.results} == {"provider_unavailable"}


async def test_empty_request_makes_no_calls() -> None:
    setup = _recorded_setup()

    labeling = await setup.label(LabelingRequest(job_id=uuid4(), items=()))

    assert labeling.results == ()
    assert setup.http.requests == []
    assert setup.sinks == []
