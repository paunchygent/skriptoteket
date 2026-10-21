"""Workspace-lane worker tests for partial AI answer-key suggestion results.

Purpose:
    Prove the workspace branch of the enrichment processor keeps the valid
    answers it already obtained when a later question returns an invalid
    answer or the provider fails (F1 of TASK-SKRIPT-39-04-07): an invalid
    answer skips only its own question and later questions still run, a
    provider failure fails the job while the earlier valid suggestions stay
    stored on it, and a failure on the first question stores no suggestions.

Relationships:
    - Exercises `application.curated_apps.handlers.exam_answer_key_enrichment_jobs`
      through the workspace harness and scripted providers in
      `workspace_enrichment_job_support`.
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
    StructuredLLMBackendFailureCode,
)
from tests.unit.application.curated_apps.handlers.workspace_enrichment_job_support import (
    ScriptedProvider,
    SequenceProvider,
    WorkspaceHarness,
    provider_error,
    three_unkeyed_choice_document,
)

pytestmark = pytest.mark.unit


async def test_one_invalid_answer_keeps_valid_answers_and_continues_to_later_questions() -> None:
    document = three_unkeyed_choice_document(document_id=uuid4())
    provider = SequenceProvider(
        [
            {"correct_alternative_ids": [2]},
            {"correct_alternative_ids": [9]},
            {"correct_alternative_ids": [1]},
        ]
    )
    harness = WorkspaceHarness(provider=provider, document=document)
    job = await harness.seed_claimed_job()

    finished = await harness.handler.handle(job=job)

    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED
    assert provider.call_count == 3
    payload = WorkspaceAnswerKeySuggestionsPayload.model_validate(
        finished.workspace_suggestions_json
    )
    assert [entry.item_id for entry in payload.suggestions] == ["item_001", "item_003"]
    assert payload.suggestions[0].suggestion.correct_choice_ids == ("choice_002",)
    assert payload.suggestions[1].suggestion.correct_choice_ids == ("choice_001",)


async def test_valid_answer_survives_a_later_provider_timeout_with_failover() -> None:
    document = three_unkeyed_choice_document(document_id=uuid4())
    timeout = provider_error(StructuredLLMBackendFailureCode.PROVIDER_TIMEOUT)
    provider = ScriptedProvider([{"correct_alternative_ids": [2]}, timeout, timeout])
    harness = WorkspaceHarness(provider=provider, document=document)
    job = await harness.seed_claimed_job()

    finished = await harness.handler.handle(job=job)

    # Question 1 answered, question 2 times out on primary and failover,
    # question 3 is never attempted after the terminal failure.
    assert provider.call_count == 3
    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.FAILED
    assert finished.last_error == "provider_timeout"
    payload = WorkspaceAnswerKeySuggestionsPayload.model_validate(
        finished.workspace_suggestions_json
    )
    assert [entry.item_id for entry in payload.suggestions] == ["item_001"]
    assert payload.suggestions[0].suggestion.correct_choice_ids == ("choice_002",)


async def test_valid_answer_survives_an_invalid_answer_then_a_provider_error() -> None:
    document = three_unkeyed_choice_document(document_id=uuid4())
    provider = ScriptedProvider(
        [
            {"correct_alternative_ids": [2]},
            {"correct_alternative_ids": [9]},
            provider_error(StructuredLLMBackendFailureCode.PROVIDER_REFUSAL),
        ]
    )
    harness = WorkspaceHarness(provider=provider, document=document)
    job = await harness.seed_claimed_job()

    finished = await harness.handler.handle(job=job)

    assert provider.call_count == 3
    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.FAILED
    assert finished.last_error == "provider_refusal"
    payload = WorkspaceAnswerKeySuggestionsPayload.model_validate(
        finished.workspace_suggestions_json
    )
    assert [entry.item_id for entry in payload.suggestions] == ["item_001"]


async def test_valid_answer_survives_a_failed_failover() -> None:
    three = three_unkeyed_choice_document(document_id=uuid4())
    document = three.model_copy(update={"items": three.items[:2]})
    timeout = provider_error(StructuredLLMBackendFailureCode.PROVIDER_TIMEOUT)
    provider = ScriptedProvider([{"correct_alternative_ids": [2]}, timeout, timeout])
    harness = WorkspaceHarness(provider=provider, document=document)
    job = await harness.seed_claimed_job()

    finished = await harness.handler.handle(job=job)

    # Question 1 answered; question 2 times out on primary and on failover.
    assert provider.call_count == 3
    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.FAILED
    assert finished.last_error == "provider_timeout"
    payload = WorkspaceAnswerKeySuggestionsPayload.model_validate(
        finished.workspace_suggestions_json
    )
    assert [entry.item_id for entry in payload.suggestions] == ["item_001"]


async def test_provider_failure_on_the_first_question_keeps_no_suggestions() -> None:
    document = three_unkeyed_choice_document(document_id=uuid4())
    provider = ScriptedProvider([provider_error(StructuredLLMBackendFailureCode.PROVIDER_REFUSAL)])
    harness = WorkspaceHarness(provider=provider, document=document)
    job = await harness.seed_claimed_job()

    finished = await harness.handler.handle(job=job)

    assert provider.call_count == 1
    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.FAILED
    assert finished.last_error == "provider_refusal"
    assert finished.workspace_suggestions_json is None
