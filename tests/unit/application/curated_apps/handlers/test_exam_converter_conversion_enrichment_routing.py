"""Routing tests for the in-process conversion submit handler.

Purpose:
    Prove readiness parity at the submit boundary: source-keyed and
    overlay-keyed uploads keep the synchronous ST-SKRIPT-39-01 path, a
    disabled answer-key lane changes nothing, and only overlay-free unkeyed
    exams enqueue one enrichment worker job without blocking the request.

Relationships:
    - Exercises `application.curated_apps.handlers.exam_converter_conversions`
      with in-memory protocol fakes.
"""

from __future__ import annotations

import asyncio

import pytest

from skriptoteket.application.curated_apps.conversion_hub import (
    ConversionHubJobStatus,
)
from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJobStatus,
)
from tests.unit.application.curated_apps.handlers.enrichment_routing_test_support import (
    RoutingHarness,
    make_actor,
    make_upload,
)

pytestmark = pytest.mark.unit


async def test_unkeyed_upload_enqueues_one_enrichment_job_without_converting() -> None:
    harness = RoutingHarness(enrichment_enabled=True)

    result = await harness.handler.handle(
        actor=make_actor(),
        upload=make_upload(keyed=False),
        overlay_bytes=None,
        correlation_id=None,
    )

    assert result.status is ConversionHubJobStatus.SUBMITTED
    assert harness.producer.calls == 0
    assert len(harness.enrichment_jobs.jobs) == 1
    enrichment_job = next(iter(harness.enrichment_jobs.jobs.values()))
    assert enrichment_job.status is ExamAnswerKeyEnrichmentJobStatus.QUEUED
    assert enrichment_job.conversion_job_id == result.job_id
    assert enrichment_job.source_dxe == make_upload(keyed=False).file_bytes


async def test_repeated_native_submission_returns_the_existing_job() -> None:
    harness = RoutingHarness(enrichment_enabled=True)
    actor = make_actor()

    first = await harness.handler.handle(
        actor=actor,
        upload=make_upload(keyed=False),
        overlay_bytes=None,
        correlation_id="corr-first",
        idempotency_key="same-native-submit",
    )
    second = await harness.handler.handle(
        actor=actor,
        upload=make_upload(keyed=False),
        overlay_bytes=None,
        correlation_id="corr-response-retry",
        idempotency_key="same-native-submit",
    )

    assert second.job_id == first.job_id
    assert second.idempotent_replay is True
    assert len(harness.jobs.jobs) == 1
    assert len(harness.enrichment_jobs.jobs) == 1


async def test_repeated_successful_native_submission_remains_idempotent() -> None:
    harness = RoutingHarness(enrichment_enabled=True)
    actor = make_actor()

    first = await harness.handler.handle(
        actor=actor,
        upload=make_upload(keyed=True),
        overlay_bytes=None,
        correlation_id="corr-first",
        idempotency_key="successful-native-submit",
    )
    second = await harness.handler.handle(
        actor=actor,
        upload=make_upload(keyed=True),
        overlay_bytes=None,
        correlation_id="corr-retry",
        idempotency_key="successful-native-submit",
    )

    assert first.status is ConversionHubJobStatus.SUCCEEDED
    assert second.job_id == first.job_id
    assert second.status is ConversionHubJobStatus.SUCCEEDED
    assert second.idempotent_replay is True
    assert harness.producer.calls == 1


async def test_repeated_native_submission_after_failure_creates_a_fresh_attempt() -> None:
    harness = RoutingHarness(enrichment_enabled=True)
    actor = make_actor()

    first = await harness.handler.handle(
        actor=actor,
        upload=make_upload(keyed=False),
        overlay_bytes=None,
        correlation_id="corr-first",
        idempotency_key="failed-native-submit",
    )
    failed = harness.jobs.jobs[first.job_id].model_copy(
        update={
            "status": ConversionHubJobStatus.FAILED,
            "error_message": "conversion failed",
        }
    )
    await harness.jobs.update(job=failed)

    second = await harness.handler.handle(
        actor=actor,
        upload=make_upload(keyed=False),
        overlay_bytes=None,
        correlation_id="corr-retry",
        idempotency_key="failed-native-submit",
    )

    assert second.job_id != first.job_id
    assert second.idempotent_replay is False
    assert second.status is ConversionHubJobStatus.SUBMITTED
    assert len(harness.jobs.jobs) == 2
    assert len(harness.enrichment_jobs.jobs) == 2
    assert harness.jobs.jobs[first.job_id].submission_idempotency_key is None


async def test_concurrent_native_submission_enriches_only_the_acquired_job() -> None:
    harness = RoutingHarness(enrichment_enabled=True)
    actor = make_actor()

    first, second = await asyncio.gather(
        harness.handler.handle(
            actor=actor,
            upload=make_upload(keyed=False),
            overlay_bytes=None,
            correlation_id="corr-first",
            idempotency_key="same-concurrent-submit",
        ),
        harness.handler.handle(
            actor=actor,
            upload=make_upload(keyed=False),
            overlay_bytes=None,
            correlation_id="corr-second",
            idempotency_key="same-concurrent-submit",
        ),
    )

    assert first.job_id == second.job_id
    assert sorted((first.idempotent_replay, second.idempotent_replay)) == [False, True]
    assert len(harness.jobs.jobs) == 1
    assert len(harness.enrichment_jobs.jobs) == 1


async def test_advisory_retry_identity_creates_a_distinct_enrichment_attempt() -> None:
    harness = RoutingHarness(enrichment_enabled=True)
    actor = make_actor()

    first = await harness.handler.handle(
        actor=actor,
        upload=make_upload(keyed=False),
        overlay_bytes=None,
        correlation_id="corr-first",
        idempotency_key="native-submit-retry-1",
        advisory_retry_attempt=1,
    )
    second = await harness.handler.handle(
        actor=actor,
        upload=make_upload(keyed=False),
        overlay_bytes=None,
        correlation_id="corr-second",
        idempotency_key="native-submit-retry-2",
        advisory_retry_attempt=2,
    )

    assert second.job_id != first.job_id
    retry_identities = {job.retry_identity for job in harness.enrichment_jobs.jobs.values()}
    assert retry_identities == {
        "native-submit-retry-1:advisory:1",
        "native-submit-retry-2:advisory:2",
    }


async def test_mixed_manual_marking_upload_enqueues_supported_unkeyed_items() -> None:
    harness = RoutingHarness(enrichment_enabled=True)

    result = await harness.handler.handle(
        actor=make_actor(),
        upload=make_upload(keyed=False, include_open_ended=True),
        overlay_bytes=None,
        correlation_id=None,
    )

    assert result.status is ConversionHubJobStatus.SUBMITTED
    assert harness.producer.calls == 0
    assert len(harness.enrichment_jobs.jobs) == 1


async def test_asset_bearing_mixed_upload_still_enqueues_enrichment() -> None:
    harness = RoutingHarness(enrichment_enabled=True)

    result = await harness.handler.handle(
        actor=make_actor(),
        upload=make_upload(keyed=False, include_asset_item=True),
        overlay_bytes=None,
        correlation_id=None,
    )

    assert result.status is ConversionHubJobStatus.SUBMITTED
    assert harness.producer.calls == 0
    assert len(harness.enrichment_jobs.jobs) == 1


async def test_source_keyed_upload_keeps_the_synchronous_path() -> None:
    harness = RoutingHarness(enrichment_enabled=True)

    result = await harness.handler.handle(
        actor=make_actor(),
        upload=make_upload(keyed=True),
        overlay_bytes=None,
        correlation_id=None,
    )

    assert result.status is ConversionHubJobStatus.SUCCEEDED
    assert harness.producer.calls == 1
    assert harness.enrichment_jobs.jobs == {}


async def test_overlay_upload_keeps_the_synchronous_path() -> None:
    harness = RoutingHarness(enrichment_enabled=True)

    result = await harness.handler.handle(
        actor=make_actor(),
        upload=make_upload(keyed=False),
        overlay_bytes=b"{}",
        correlation_id=None,
    )

    assert result.status is ConversionHubJobStatus.SUCCEEDED
    assert harness.producer.calls == 1
    assert harness.enrichment_jobs.jobs == {}


async def test_disabled_answer_key_lane_changes_nothing_for_unkeyed_uploads() -> None:
    harness = RoutingHarness(enrichment_enabled=False)

    result = await harness.handler.handle(
        actor=make_actor(),
        upload=make_upload(keyed=False),
        overlay_bytes=None,
        correlation_id=None,
    )

    assert result.status is ConversionHubJobStatus.SUCCEEDED
    assert harness.producer.calls == 1
    assert harness.enrichment_jobs.jobs == {}
