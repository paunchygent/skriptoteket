"""A many-family exam converts every family within the real daily token lease (D25, D37, R-F2).

The production pipeline runs at the default settings (one question family per converter
request, the default daily token limit) on the PostgreSQL lease ledger. The converter holds
every batch request open until all of them have reached it, so every batch reservation is
outstanding at once; a batch whose reservation the lease refused would never arrive.
"""

import asyncio
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_serial_uow import (
    SerializedUnitOfWork,
)
from skriptoteket.config import Settings
from skriptoteket.di.docx_conversion import build_docx_conversion_pipeline
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMProviderProfile,
    StructuredLLMRequest,
    StructuredLLMResponse,
    StructuredLLMUsage,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_token_lease import (
    lease_utc_day,
)
from skriptoteket.infrastructure.db.uow import SQLAlchemyUnitOfWork
from skriptoteket.infrastructure.repositories.exam_answer_key_token_leases import (
    PostgreSQLAnswerKeyTokenLeaseRepository,
)
from tests.fixtures.time_fixtures import FixedClock
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import (
    NoSleep,
    RecordingProgress,
    Replay,
    ReplayProvider,
    decisions_client,
)

pytestmark = [pytest.mark.integration, pytest.mark.docker, pytest.mark.asyncio(loop_scope="module")]

_EXAM = "bf26_diagnostic_grammar_test_ht26_med_facit"
_API_KEY = "fixture-key"


class _HoldAllBatches(ReplayProvider):
    """Serve grouping and labels from the recordings; hold every converter batch open.

    Each held batch is answered with an empty envelope once every family's batch has
    arrived, so its chunks become review items holding their source text.
    """

    def __init__(self) -> None:
        super().__init__(_EXAM)
        self.families = 0
        self.held: list[StructuredLLMRequest] = []
        self.all_arrived = asyncio.Event()

    async def complete_structured(
        self, *, request: StructuredLLMRequest, profile: StructuredLLMProviderProfile
    ) -> StructuredLLMResponse:
        if not request.item_id.startswith("docx_w"):
            return await super().complete_structured(request=request, profile=profile)
        self.held.append(request)
        if len(self.held) == self.families:
            self.all_arrived.set()
        await self.all_arrived.wait()
        return StructuredLLMResponse(
            content={"title": None, "instructions": [], "answer_key_anchors": [], "items": []},
            finish_reason="completed",
            usage=StructuredLLMUsage(),
        )


async def test_a_104_family_exam_in_one_family_batches_reserves_them_all_under_the_daily_limit(
    session_factory: async_sessionmaker[AsyncSession],
) -> None:
    # One family per batch is the most batches an exam can hold at once.
    settings = Settings.model_construct(
        LLM_ANSWER_KEY_ENABLED=True,
        OPENAI_LLM_ANSWER_KEY_API_KEY=_API_KEY,
        LLM_DOCX_BATCH_FAMILIES=1,
    )
    provider = _HoldAllBatches()
    progress = RecordingProgress()
    now = datetime.now(UTC)

    async with session_factory() as session:
        leases = PostgreSQLAnswerKeyTokenLeaseRepository(
            session, daily_token_limit=settings.LLM_ANSWER_KEY_DAILY_TOKEN_LIMIT
        )
        replay = Replay(
            exam=_EXAM,
            pipeline=build_docx_conversion_pipeline(
                client=decisions_client(_EXAM),
                provider=provider,
                sleeper=NoSleep(),
                leases=leases,
                uow=SerializedUnitOfWork(SQLAlchemyUnitOfWork(session)),
                clock=FixedClock(now),
                settings=settings,
                progress=progress,
            ),
            provider=provider,
            progress=progress,
        )
        conversion = asyncio.create_task(replay.pipeline.convert(job=replay.job()))
        while not progress.outlines:
            await asyncio.sleep(0)
        provider.families = len(progress.outlines[0].questions)
        assert provider.families == 104

        await asyncio.wait_for(provider.all_arrived.wait(), timeout=60)
        outstanding = await leases.day_usage(utc_day=lease_utc_day(now))
        outcome = await asyncio.wait_for(conversion, timeout=60)

    assert len({request.item_id for request in provider.held}) == 104
    assert outstanding.charged_tokens <= settings.LLM_ANSWER_KEY_DAILY_TOKEN_LIMIT
    assert all(
        request.max_output_tokens == settings.LLM_DOCX_BATCH_OUTPUT_TOKENS_PER_FAMILY
        for request in provider.held
    )
    assert "lease_refused" not in {event.code for event in outcome.result.events}
    assert outcome.update.pending == ()
