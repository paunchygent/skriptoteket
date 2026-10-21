"""Workspace-lane worker tests for AI answer-key suggestions.

Purpose:
    Prove the workspace branch of the enrichment processor runs on the
    answer-key views sent with the job (TASK-SKRIPT-39-04-07): the provider
    is called once per item, the suggestions are stored on the job itself
    with their fingerprints and provider lineage, no overlay is written, and
    the conversion producer is never called. Failure paths finish the job
    without touching conversion jobs.

Relationships:
    - Exercises `application.curated_apps.handlers.exam_answer_key_enrichment_jobs`
      against the shared in-memory protocol fakes in
      `answer_key_enrichment_test_support` (the DXE lane stays untouched).
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJobStatus,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_enrichment import (
    WorkspaceAnswerKeySuggestionsPayload,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMUsage,
)
from skriptoteket.domain.curated_apps.exam_workspace.answer_key_view import (
    answer_key_fingerprint,
)
from tests.unit.application.curated_apps.handlers.answer_key_enrichment_test_support import (
    StubProvider,
)
from tests.unit.application.curated_apps.handlers.workspace_enrichment_job_support import (
    WorkspaceHarness,
    unkeyed_choice_document,
)
from tests.unit.domain.curated_apps.exam_workspace.matching_recording_support import (
    document_of,
    recorded_matching_items,
)

pytestmark = pytest.mark.unit


async def test_workspace_job_stores_suggestions_on_the_job_without_an_overlay() -> None:
    document = unkeyed_choice_document(document_id=uuid4())
    harness = WorkspaceHarness(
        provider=StubProvider(
            content={"correct_alternative_ids": [2]},
            usage=StructuredLLMUsage(total_tokens=190),
        ),
        document=document,
    )
    job = await harness.seed_claimed_job()

    finished = await harness.handler.handle(job=job)

    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED
    assert harness.provider.call_count == 1

    payload = WorkspaceAnswerKeySuggestionsPayload.model_validate(
        finished.workspace_suggestions_json
    )
    assert len(payload.suggestions) == 1
    arrived = payload.suggestions[0]
    assert arrived.item_id == "item_001"
    assert arrived.suggestion.correct_choice_ids == ("choice_002",)
    assert arrived.suggestion.provider_profile_id == "openai-gpt-5.6-luna"
    assert arrived.suggestion.model == "gpt-5.6-luna"
    assert arrived.suggestion.prompt_template_version == "digiexam_choice_answer_key_prompt_v1"
    assert arrived.suggestion.fingerprint == answer_key_fingerprint(document.items[0], None)


async def test_workspace_job_without_sent_content_fails_closed() -> None:
    document = unkeyed_choice_document(document_id=uuid4())
    provider = StubProvider(
        content={"correct_alternative_ids": [2]},
        usage=StructuredLLMUsage(total_tokens=190),
    )
    harness = WorkspaceHarness(provider=provider, document=document)
    job = await harness.seed_claimed_job()
    harness.enrichment_jobs.jobs[job.id] = job.model_copy(update={"workspace_request_json": None})

    finished = await harness.handler.handle(job=harness.enrichment_jobs.jobs[job.id])

    assert provider.call_count == 0
    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.FAILED
    assert finished.last_error == "workspace_request_missing"


async def test_invalid_workspace_model_output_fails_without_a_suggestion() -> None:
    document = unkeyed_choice_document(document_id=uuid4())
    harness = WorkspaceHarness(
        provider=StubProvider(
            content={"correct_alternative_ids": [9]},
            usage=StructuredLLMUsage(total_tokens=50),
        ),
        document=document,
    )
    job = await harness.seed_claimed_job()

    finished = await harness.handler.handle(job=job)

    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.FAILED
    assert finished.last_error == "llm_output_invalid"
    assert finished.workspace_suggestions_json is None


async def test_matching_workspace_job_stores_pairs_for_recorded_unkeyed_items() -> None:
    items = recorded_matching_items()
    document = document_of(*items)
    harness = WorkspaceHarness(
        provider=StubProvider(
            content={
                "pairs": [
                    {"left_id": 1, "right_id": 3},
                    {"left_id": 2, "right_id": 2},
                    {"left_id": 3, "right_id": 1},
                ]
            },
            usage=StructuredLLMUsage(total_tokens=120),
        ),
        document=document,
    )
    job = await harness.seed_claimed_job()

    finished = await harness.handler.handle(job=job)

    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED
    assert harness.provider.call_count == len(items)
    payload = WorkspaceAnswerKeySuggestionsPayload.model_validate(
        finished.workspace_suggestions_json
    )
    assert [entry.item_id for entry in payload.suggestions] == [item.item_id for item in items]
    for entry in payload.suggestions:
        assert [(p.left_id, p.right_id) for p in entry.suggestion.match_pairs] == [
            ("left_001", "right_003"),
            ("left_002", "right_002"),
            ("left_003", "right_001"),
        ]
        assert entry.suggestion.prompt_template_version == "workspace_matching_answer_key_prompt_v2"


async def test_matching_workspace_job_fails_when_a_left_entry_is_left_unpaired() -> None:
    document = document_of(*recorded_matching_items())
    harness = WorkspaceHarness(
        provider=StubProvider(
            content={"pairs": [{"left_id": 1, "right_id": 3}, {"left_id": 2, "right_id": 2}]},
            usage=StructuredLLMUsage(total_tokens=120),
        ),
        document=document,
    )
    job = await harness.seed_claimed_job()

    finished = await harness.handler.handle(job=job)

    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.FAILED
    assert finished.last_error == "llm_output_invalid"
