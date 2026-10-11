"""Two-pass item-type labeler behind the daily token lease (TASK-SKRIPT-39-05-04 D23).

The first pass is the real Decisions adapter replaying the recorded 24-question exchange
over ``httpx.MockTransport``; no live second-pass reply is recorded, so the second pass is a
scripted fake. The lease repository, UoW and clock are stand-ins.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import pytest

from skriptoteket.application.curated_apps.item_type_labeling import (
    FIRST_PASS_LEASE_ITEM_ID,
    TwoPassItemTypeLabeler,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_token_lease import (
    AnswerKeyTokenLease,
    AnswerKeyTokenLeaseRefused,
    AnswerKeyTokenLeaseState,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.exam_answer_key import AnswerKeyTokenLeaseRepositoryProtocol
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
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from tests.unit.infrastructure.llm.decisions_item_labeler_support import (
    CORPUS_24,
    Harness,
    always,
    load,
    replay,
    request_for,
    unavailable,
)

pytestmark = pytest.mark.unit

_NOW = datetime(2026, 10, 11, 12, tzinfo=UTC)
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
        self.events: list[str] = []
        self.reserved: dict[UUID, tuple[str, int]] = {}
        self.reconciled: dict[str, int] = {}
        self.refused_ids: set[str] = set()
        self.http = Harness(first_pass_responder)
        self.second = second_pass or _FakeSecondPass()
        self.leases = AsyncMock(spec=AnswerKeyTokenLeaseRepositoryProtocol)
        self.leases.reserve.side_effect = self._reserve
        self.leases.reconcile.side_effect = self._reconcile
        self.uow = AsyncMock(spec=UnitOfWorkProtocol)
        clock = Mock(spec=ClockProtocol)
        clock.now.return_value = _NOW
        self.first = self.http.labeler()
        self.labeler = TwoPassItemTypeLabeler(
            first_pass=self.first,
            second_pass=self.second,
            leases=self.leases,
            uow=self.uow,
            clock=clock,
        )
        self.sinks: list[tuple[ItemTypeLabelResult, ...]] = []

    async def _reserve(self, **kwargs: object) -> AnswerKeyTokenLease:
        item_id = str(kwargs["item_id"])
        self.events.append(f"reserve:{item_id}")
        if item_id in self.refused_ids:
            raise AnswerKeyTokenLeaseRefused(
                utc_day=_NOW.date(), requested_tokens=10, available_tokens=0, resets_at=_NOW
            )
        lease = AnswerKeyTokenLease(
            lease_id=uuid4(),
            utc_day=_NOW.date(),
            reserved_tokens=int(str(kwargs["requested_tokens"])),
            state=AnswerKeyTokenLeaseState.RESERVED,
        )
        self.reserved[lease.lease_id] = (item_id, int(str(kwargs["requested_tokens"])))
        return lease

    async def _reconcile(self, **kwargs: object) -> None:
        item_id, _ = self.reserved[kwargs["lease_id"]]  # type: ignore[index]
        self.reconciled[item_id] = int(str(kwargs["actual_tokens"]))

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


async def test_refused_first_pass_lease_stops_before_any_network_call() -> None:
    request, _ = _recorded()
    setup = _recorded_setup()
    setup.refused_ids = {FIRST_PASS_LEASE_ITEM_ID}

    with pytest.raises(ItemTypeLabelerError) as raised:
        await setup.label(request)

    assert raised.value.code == "lease_refused"
    assert setup.http.requests == []
    assert setup.second.asked == []
    assert setup.sinks == []


async def test_first_pass_is_reserved_before_the_network_and_reconciled_with_measured_tokens() -> (
    None
):
    request, _ = _recorded()
    setup = _recorded_setup()

    await setup.label(request)

    assert setup.events[0] == f"reserve:{FIRST_PASS_LEASE_ITEM_ID}"
    (first_lease,) = [r for r in setup.reserved.values() if r[0] == FIRST_PASS_LEASE_ITEM_ID]
    assert first_lease[1] == setup.first.estimate_input_tokens(request=request)
    recorded_tokens = load(CORPUS_24)["exchanges"][0]["body"]["usage"]["input_tokens"]
    assert setup.reconciled[FIRST_PASS_LEASE_ITEM_ID] == recorded_tokens
    reserve_call = setup.leases.reserve.await_args_list[0].kwargs
    assert reserve_call["job_id"] == request.job_id
    assert reserve_call["provider_profile_id"] == "openai-decisions-gpt-6-luna"


async def test_each_escalated_question_is_leased_alone_and_reconciled_with_input_plus_output() -> (
    None
):
    request, below = _recorded()
    assert below
    setup = _recorded_setup()

    labeling = await setup.label(request)

    assert sorted(setup.second.asked) == sorted(below)
    by_id = {item.item_id: item for item in request.items}
    for item_id in below:
        lease_key = f"label_b:{item_id}"
        (reservation,) = [r for r in setup.reserved.values() if r[0] == lease_key]
        assert reservation[1] == setup.second.estimate_tokens(item=by_id[item_id])
        assert setup.reconciled[lease_key] == _B_INPUT_TOKENS + _B_OUTPUT_TOKENS
    assert set(setup.reconciled) == {FIRST_PASS_LEASE_ITEM_ID} | {f"label_b:{i}" for i in below}
    recorded_tokens = load(CORPUS_24)["exchanges"][0]["body"]["usage"]["input_tokens"]
    assert labeling.usage.input_tokens == recorded_tokens + _B_INPUT_TOKENS * len(below)
    for call in setup.leases.reserve.await_args_list:
        assert call.kwargs["job_id"] == request.job_id
    b_calls = [
        c
        for c in setup.leases.reserve.await_args_list
        if c.kwargs["item_id"] != "item_type_labeling"
    ]
    assert {c.kwargs["provider_profile_id"] for c in b_calls} == {_B_PROFILE}


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


async def test_second_pass_failure_leaves_one_question_unresolved_and_keeps_the_rest() -> None:
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
    assert broken.label is ItemTypeLabel.UNRESOLVED
    assert broken.failure_code == "provider_unavailable"
    assert broken.decided_by is LabelPass.SECOND
    assert broken.first_pass is not None
    assert f"label_b:{failing}" not in setup.reconciled
    others = [r for r in labeling.results if r.item_id in below and r.item_id != failing]
    assert others
    assert all(r.label is _B_LABEL and r.failure_code is None for r in others)
    assert labeling.usage.input_tokens is None


async def test_refused_second_pass_lease_leaves_that_question_unresolved_without_calling_b() -> (
    None
):
    request, below = _recorded()
    starved = sorted(below)[0]
    setup = _recorded_setup()
    setup.refused_ids = {f"label_b:{starved}"}

    labeling = await setup.label(request)

    result = next(r for r in labeling.results if r.item_id == starved)
    assert result.label is ItemTypeLabel.UNRESOLVED
    assert result.failure_code == "lease_refused"
    assert starved not in setup.second.asked
    assert sorted(setup.second.asked) == sorted(below - {starved})


async def test_unmeasured_second_pass_usage_keeps_its_reservation_charged() -> None:
    request, below = _recorded()
    unmeasured = sorted(below)[0]
    setup = _recorded_setup(
        _FakeSecondPass({unmeasured: SecondPassLabel(_B_LABEL, _B_INPUT_TOKENS, None)})
    )

    labeling = await setup.label(request)

    assert f"label_b:{unmeasured}" in {r[0] for r in setup.reserved.values()}
    assert f"label_b:{unmeasured}" not in setup.reconciled
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
    assert result.label is ItemTypeLabel.UNRESOLVED
    assert result.failure_code is None


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
    assert FIRST_PASS_LEASE_ITEM_ID not in setup.reconciled
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


async def test_failed_first_pass_with_failing_second_pass_leaves_every_question_unresolved() -> (
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


async def test_failed_reconciliation_still_returns_every_label() -> None:
    request, _ = _recorded()
    setup = _recorded_setup()
    setup.leases.reconcile.side_effect = RuntimeError("database unavailable")

    labeling = await setup.label(request)

    assert [r.item_id for r in labeling.results] == [i.item_id for i in request.items]
    assert all(r.failure_code is None for r in labeling.results)


async def test_empty_request_spends_nothing() -> None:
    setup = _recorded_setup()

    labeling = await setup.label(LabelingRequest(job_id=uuid4(), items=()))

    assert labeling.results == ()
    assert setup.events == []
    assert setup.http.requests == []
    assert setup.sinks == []
