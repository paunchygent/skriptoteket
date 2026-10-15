"""Second-wave questions convert as their own labels arrive (D25, D37, R-F6).

The production pipeline replays the diagnostic grammar exam, whose first labeling pass escalates
six questions to the second pass. One second-pass call is held open; every other escalated
question must reach the converter and the editor while it is still outstanding.
"""

import asyncio

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMProviderProfile,
    StructuredLLMRequest,
    StructuredLLMResponse,
)
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import (
    RECORDINGS,
    ReplayProvider,
    build_replay,
)

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

_EXAM = "bf26_diagnostic_grammar_test_ht26_med_facit"
_ESCALATED = sorted(p.stem.removeprefix("label_b_") for p in (RECORDINGS / _EXAM).glob("label_b_*"))
_HELD = _ESCALATED[0]


class _HeldLabel(ReplayProvider):
    """Hold one question's second-pass label until the test releases it.

    Holding a label changes the order second-pass labels arrive in, and with it the
    second-wave batch numbers, so a second-wave request is served the recording of its
    own question by anchor.
    """

    def __init__(self) -> None:
        super().__init__(_EXAM)
        self.release = asyncio.Event()

    async def complete_structured(
        self, *, request: StructuredLLMRequest, profile: StructuredLLMProviderProfile
    ) -> StructuredLLMResponse:
        if request.item_id == f"label_b:{_HELD}":
            await self.release.wait()
        return await super().complete_structured(request=request, profile=profile)


def _second_wave(provider: ReplayProvider) -> list[str]:
    return [rid for rid in provider.request_ids if rid.startswith("docx_w2-")]


async def test_a_slow_second_pass_label_does_not_delay_other_second_wave_questions():
    assert len(_ESCALATED) > 1, "the recording must escalate several questions"
    provider = _HeldLabel()
    replay = build_replay(_EXAM, provider=provider)
    conversion = asyncio.create_task(replay.pipeline.convert(job=replay.job()))

    async def others_converted() -> None:
        while not any(
            set(_ESCALATED) - {_HELD} <= set(update.filled) for update in replay.progress.updates
        ):
            await asyncio.sleep(0)

    await asyncio.wait_for(others_converted(), timeout=10)
    assert not conversion.done()
    assert len(_second_wave(provider)) == len(_ESCALATED) - 1
    assert all(_HELD not in update.filled for update in replay.progress.updates)

    provider.release.set()
    outcome = await asyncio.wait_for(conversion, timeout=10)

    second_wave = _second_wave(provider)
    assert len(second_wave) == len(set(second_wave)) == len(_ESCALATED), "batch ids collide"
    assert outcome.update.pending == ()
    assert _HELD in outcome.update.filled
    assert not [e for e in outcome.result.events if e.stage in {"provider", "batch"}]
