"""Worker-job lifecycle tests for machine answer-key enrichment.

Purpose:
    Prove the enrichment processor with a stubbed provider: lease reserved
    before the call and reconciled from reported usage, machine-proposed
    overlay persisted, conversion completed; the typed lease refusal makes
    zero provider calls and never routes to the failover; a transient Luna
    outage fails over exactly once to the GLM profile under a second lease
    from the same daily counter; provider failures never refund any lease.

Relationships:
    - Exercises `application.curated_apps.handlers.exam_answer_key_enrichment_jobs`
      against in-memory protocol fakes and an injected clock.
"""

from __future__ import annotations

from datetime import timedelta

import pytest

from skriptoteket.application.curated_apps.conversion_hub import ConversionHubJobStatus
from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJobStatus,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMBackendFailureCode,
    StructuredLLMProviderError,
    StructuredLLMResponse,
    StructuredLLMUsage,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_token_lease import (
    AnswerKeyTokenLeaseState,
    lease_utc_day,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_contracts import (
    DigiExamAnswerKeyProvenance,
)
from tests.unit.application.curated_apps.handlers.answer_key_enrichment_test_support import (
    _NOW,
    StubProvider,
)
from tests.unit.application.curated_apps.handlers.enrichment_job_harness_test_support import (
    SequenceProvider,
    _Harness,
    _unkeyed_dxe_bytes,
)

pytestmark = pytest.mark.unit


def _timeout_error(provider_id: str) -> StructuredLLMProviderError:
    return StructuredLLMProviderError(
        failure_code=StructuredLLMBackendFailureCode.PROVIDER_TIMEOUT,
        message="Structured provider request timed out.",
        provider_id=provider_id,
    )


async def test_successful_job_reserves_reconciles_and_completes_conversion() -> None:
    harness = _Harness(
        provider=StubProvider(
            content={"correct_alternative_ids": [2]},
            usage=StructuredLLMUsage(total_tokens=190),
        )
    )
    job = await harness.seed_claimed_job()

    finished = await harness.handler.handle(job=job)

    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED
    assert harness.provider.call_count == 1
    leases = list(harness.leases.leases.values())
    assert len(leases) == 1
    assert leases[0].state is AnswerKeyTokenLeaseState.RECONCILED
    assert leases[0].actual_tokens == 190
    assert job.conversion_job_id is not None
    conversion_job = harness.conversion_jobs.jobs[job.conversion_job_id]
    assert conversion_job.status is ConversionHubJobStatus.SUCCEEDED
    assert conversion_job.upstream_job_id is None
    assert harness.producer.overlay_key_provenance is (
        DigiExamAnswerKeyProvenance.MACHINE_PROPOSED_KEY
    )
    assert harness.producer.overlay_bytes is not None
    assert job.conversion_job_id in harness.artifacts.stored
    proposal = harness.proposed_overlays.records[0]
    assert proposal.conversion_job_id == job.conversion_job_id
    assert proposal.provider_profile_id == "openai-gpt-5.6-luna"
    assert proposal.model == "gpt-5.6-luna"
    overlay_items = proposal.overlay_json["items"]
    assert isinstance(overlay_items, list)
    assert len(overlay_items) == 1


async def test_mixed_exam_enriches_only_supported_item_and_completes_conversion() -> None:
    harness = _Harness(
        provider=StubProvider(
            content={"correct_alternative_ids": [2]},
            usage=StructuredLLMUsage(total_tokens=190),
        )
    )
    job = await harness.seed_claimed_job(source_dxe=_unkeyed_dxe_bytes(include_open_ended=True))

    finished = await harness.handler.handle(job=job)

    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED
    assert harness.provider.call_count == 1
    assert len(harness.leases.leases) == 1
    proposal = harness.proposed_overlays.records[0]
    overlay_items = proposal.overlay_json["items"]
    assert isinstance(overlay_items, list)
    assert len(overlay_items) == 1
    overlay_item = overlay_items[0]
    assert isinstance(overlay_item, dict)
    assert overlay_item["item_id"] == "item-001"
    assert harness.producer.overlay_key_provenance is (
        DigiExamAnswerKeyProvenance.MACHINE_PROPOSED_KEY
    )
    assert job.conversion_job_id is not None
    conversion_job = harness.conversion_jobs.jobs[job.conversion_job_id]
    assert conversion_job.status is ConversionHubJobStatus.SUCCEEDED


async def test_lease_refusal_fails_closed_with_zero_provider_calls() -> None:
    provider = StubProvider(
        content={"correct_alternative_ids": [2]},
        usage=StructuredLLMUsage(total_tokens=190),
    )
    harness = _Harness(provider=provider, daily_token_limit=10)
    job = await harness.seed_claimed_job()

    finished = await harness.handler.handle(job=job)

    assert provider.call_count == 0
    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.FAILED
    assert finished.last_error == "daily_token_lease_exhausted"
    assert job.conversion_job_id is not None
    conversion_job = harness.conversion_jobs.jobs[job.conversion_job_id]
    assert conversion_job.status is ConversionHubJobStatus.SUCCEEDED
    assert conversion_job.error_message is not None
    assert "2026-08-30 00:00" in conversion_job.error_message
    assert harness.proposed_overlays.records == []


async def test_transient_luna_failure_fails_over_once_and_succeeds_via_glm() -> None:
    provider = SequenceProvider(
        outcomes=(
            _timeout_error("openai-gpt-5.6-luna"),
            StructuredLLMResponse(
                content={"correct_alternative_ids": [2]},
                finish_reason="stop",
                usage=StructuredLLMUsage(total_tokens=40),
            ),
        )
    )
    harness = _Harness(provider=provider)
    job = await harness.seed_claimed_job()

    finished = await harness.handler.handle(job=job)

    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED
    assert [profile.provider_id for profile in provider.profiles] == [
        "openai-gpt-5.6-luna",
        "openrouter-glm-5.3-flash",
    ]
    assert len(harness.leases.leases) == 2
    primary_lease = harness.leases.leases_for_profile("openai-gpt-5.6-luna")[0]
    failover_lease = harness.leases.leases_for_profile("openrouter-glm-5.3-flash")[0]
    assert primary_lease.state is AnswerKeyTokenLeaseState.RESERVED
    assert primary_lease.actual_tokens is None
    assert failover_lease.state is AnswerKeyTokenLeaseState.RECONCILED
    assert failover_lease.actual_tokens == 40
    usage = await harness.leases.day_usage(utc_day=lease_utc_day(_NOW))
    assert usage.charged_tokens == primary_lease.reserved_tokens + 40
    proposal = harness.proposed_overlays.records[0]
    assert proposal.provider_profile_id == "openrouter-glm-5.3-flash"
    assert proposal.model == "z-ai/glm-5.3-flash"
    assert job.conversion_job_id is not None
    conversion_job = harness.conversion_jobs.jobs[job.conversion_job_id]
    assert conversion_job.status is ConversionHubJobStatus.SUCCEEDED
    assert job.conversion_job_id in harness.artifacts.stored


async def test_glm_failure_after_failover_fails_job_with_both_leases_charged() -> None:
    provider = SequenceProvider(
        outcomes=(
            _timeout_error("openai-gpt-5.6-luna"),
            _timeout_error("openrouter-glm-5.3-flash"),
        )
    )
    harness = _Harness(provider=provider)
    job = await harness.seed_claimed_job()

    finished = await harness.handler.handle(job=job)

    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.FAILED
    assert finished.last_error == "provider_timeout"
    assert [profile.provider_id for profile in provider.profiles] == [
        "openai-gpt-5.6-luna",
        "openrouter-glm-5.3-flash",
    ]
    leases = list(harness.leases.leases.values())
    assert len(leases) == 2
    assert all(lease.state is AnswerKeyTokenLeaseState.RESERVED for lease in leases)
    usage = await harness.leases.day_usage(utc_day=lease_utc_day(_NOW))
    assert usage.charged_tokens == sum(lease.reserved_tokens for lease in leases)
    assert harness.proposed_overlays.records == []
    assert job.conversion_job_id is not None
    conversion_job = harness.conversion_jobs.jobs[job.conversion_job_id]
    assert conversion_job.status is ConversionHubJobStatus.SUCCEEDED


async def test_second_lease_exhaustion_stops_before_the_failover_call() -> None:
    provider = SequenceProvider(outcomes=(_timeout_error("openai-gpt-5.6-luna"),))
    harness = _Harness(provider=provider, daily_token_limit=6_000)
    job = await harness.seed_claimed_job()

    finished = await harness.handler.handle(job=job)

    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.FAILED
    assert finished.last_error == "daily_token_lease_exhausted"
    assert [profile.provider_id for profile in provider.profiles] == ["openai-gpt-5.6-luna"]
    assert len(harness.leases.leases) == 1
    assert job.conversion_job_id is not None
    conversion_job = harness.conversion_jobs.jobs[job.conversion_job_id]
    assert conversion_job.status is ConversionHubJobStatus.SUCCEEDED
    assert conversion_job.error_message is not None
    assert "2026-08-30 00:00" in conversion_job.error_message


async def test_non_transient_luna_failure_never_calls_the_failover() -> None:
    provider = SequenceProvider(
        outcomes=(
            StructuredLLMProviderError(
                failure_code=StructuredLLMBackendFailureCode.PROVIDER_HTTP_ERROR,
                message="Structured provider returned an unsuccessful HTTP status.",
                provider_id="openai-gpt-5.6-luna",
                status_code=400,
            ),
        )
    )
    harness = _Harness(provider=provider)
    job = await harness.seed_claimed_job()

    finished = await harness.handler.handle(job=job)

    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.FAILED
    assert finished.last_error == "provider_http_error"
    assert [profile.provider_id for profile in provider.profiles] == ["openai-gpt-5.6-luna"]
    leases = list(harness.leases.leases.values())
    assert len(leases) == 1
    assert leases[0].state is AnswerKeyTokenLeaseState.RESERVED
    assert leases[0].actual_tokens is None
    usage = await harness.leases.day_usage(utc_day=lease_utc_day(_NOW))
    assert usage.charged_tokens == leases[0].reserved_tokens
    assert job.conversion_job_id is not None
    conversion_job = harness.conversion_jobs.jobs[job.conversion_job_id]
    assert conversion_job.status is ConversionHubJobStatus.SUCCEEDED


async def test_invalid_model_output_fails_without_a_proposal() -> None:
    harness = _Harness(
        provider=StubProvider(
            content={"correct_alternative_ids": [9]},
            usage=StructuredLLMUsage(total_tokens=50),
        )
    )
    job = await harness.seed_claimed_job()

    finished = await harness.handler.handle(job=job)

    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.FAILED
    assert finished.last_error == "llm_output_invalid"
    leases = list(harness.leases.leases.values())
    assert leases[0].state is AnswerKeyTokenLeaseState.RECONCILED
    assert leases[0].actual_tokens == 50
    assert harness.proposed_overlays.records == []
    assert job.conversion_job_id is not None
    conversion_job = harness.conversion_jobs.jobs[job.conversion_job_id]
    assert conversion_job.status is ConversionHubJobStatus.SUCCEEDED


async def test_expired_running_job_fail_closes_both_jobs_without_calls_or_refund() -> None:
    provider = StubProvider(
        content={"correct_alternative_ids": [2]},
        usage=StructuredLLMUsage(total_tokens=190),
    )
    harness = _Harness(provider=provider)
    job = await harness.seed_claimed_job()
    await harness.leases.reserve(
        now=_NOW,
        requested_tokens=300,
        job_id=job.id,
        item_id="item-001",
        provider_profile_id="openai-gpt-5.6-luna",
    )

    still_leased = await harness.handler.fail_next_expired(
        worker_id="reaper",
        now=_NOW,
        lease_ttl=timedelta(minutes=15),
    )
    assert still_leased is None

    after_expiry = _NOW + timedelta(seconds=1800)
    failed = await harness.handler.fail_next_expired(
        worker_id="reaper",
        now=after_expiry,
        lease_ttl=timedelta(minutes=15),
    )

    assert failed is not None
    assert failed.status is ExamAnswerKeyEnrichmentJobStatus.FAILED
    assert failed.last_error == "enrichment_worker_lease_expired"
    assert failed.locked_by is None
    assert job.conversion_job_id is not None
    conversion_job = harness.conversion_jobs.jobs[job.conversion_job_id]
    assert conversion_job.status is ConversionHubJobStatus.SUCCEEDED
    assert conversion_job.error_message is not None
    assert provider.call_count == 0
    leases = list(harness.leases.leases.values())
    assert len(leases) == 1
    assert leases[0].state is AnswerKeyTokenLeaseState.RESERVED
    usage = await harness.leases.day_usage(utc_day=lease_utc_day(_NOW))
    assert usage.charged_tokens == 300
    assert (
        await harness.handler.fail_next_expired(
            worker_id="reaper",
            now=after_expiry,
            lease_ttl=timedelta(minutes=15),
        )
        is None
    )
