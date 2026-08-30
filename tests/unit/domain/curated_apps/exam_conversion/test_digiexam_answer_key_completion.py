"""Tests for machine answer-key completion planning and proposal assembly.

Purpose:
    Prove profile construction, enrichment eligibility, per-item request
    planning, provider-decision validation, and machine-proposed overlay
    application with readiness parity to the teacher-overlay path.

Relationships:
    - Exercises `domain.curated_apps.exam_conversion.digiexam_answer_key_completion`
      and the machine-provenance overlay application seam.
"""

from __future__ import annotations

import pytest
from pydantic import JsonValue

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_completion import (
    AnswerKeyEnrichmentPlanState,
    build_machine_proposed_overlay,
    manual_answer_key_from_model_content,
    overlay_json_bytes,
    plan_answer_key_candidates,
    plan_answer_key_enrichment,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMEndpointKind,
    StructuredLLMProviderProfile,
    StructuredLLMReasoningEffort,
    estimate_prompt_tokens,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_contracts import (
    DigiExamAnswerKeyProvenance,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_dxe_parser import DigiExamDxeParser
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_examnet_pdf import (
    build_digiexam_examnet_pdf_document,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_examnet_pdf_contracts import (
    DigiExamExamNetPdfStatus,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_examnet_qti_adapter import (
    build_examnet_qti_items_from_digiexam_ir,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_ingestion_overlay import (
    parse_and_apply_digiexam_ingestion_overlay,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_ir_contracts import (
    DigiExamIntermediateExam,
    DigiExamIrManualFollowUpReason,
    build_digiexam_intermediate_exam,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiPackageStatus,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_package import (
    build_examnet_qti_package_plan,
)

pytestmark = pytest.mark.unit


def _profile() -> StructuredLLMProviderProfile:
    return StructuredLLMProviderProfile(
        provider_id="openai-gpt-5.6-luna",
        model="gpt-5.6-luna",
        endpoint_kind=StructuredLLMEndpointKind.RESPONSES,
        is_remote=True,
        context_window_tokens=32_768,
        max_output_tokens=4_096,
        temperature=0.0,
        reasoning_effort=StructuredLLMReasoningEffort.LOW,
    )


def _exam(questions: list[dict[str, JsonValue]]) -> DigiExamIntermediateExam:
    parse_result = DigiExamDxeParser().parse_payload(
        {"exams": [{"questions": questions}]},
        filename="exam.dxe",
    )
    return build_digiexam_intermediate_exam(parse_result)


def _unkeyed_single_choice_question() -> dict[str, JsonValue]:
    return {
        "id": 1,
        "title": "Single without key",
        "about": "",
        "bodyHTML": "<p>Choose the Greek letter.</p>",
        "images": [],
        "maxScore": 2,
        "type": 1,
        "alternatives": [
            {"id": 1, "title": "Alpha", "about": "", "right": False},
            {"id": 2, "title": "Beta", "about": "", "right": False},
        ],
    }


def _keyed_single_choice_question() -> dict[str, JsonValue]:
    question = _unkeyed_single_choice_question()
    question["alternatives"] = [
        {"id": 1, "title": "Alpha", "about": "", "right": False},
        {"id": 2, "title": "Beta", "about": "", "right": True},
    ]
    return question


def _open_ended_question() -> dict[str, JsonValue]:
    return {
        "id": 2,
        "title": "Essay",
        "about": "",
        "bodyHTML": "<p>Explain.</p>",
        "images": [],
        "maxScore": 4,
        "type": 0,
    }


def test_profile_rejects_output_budget_at_or_above_context_window() -> None:
    with pytest.raises(ValueError):
        StructuredLLMProviderProfile(
            provider_id="openai-gpt-5.6-luna",
            model="gpt-5.6-luna",
            endpoint_kind=StructuredLLMEndpointKind.RESPONSES,
            is_remote=True,
            context_window_tokens=4_096,
            max_output_tokens=4_096,
        )


def test_unkeyed_choice_exam_is_eligible_for_enrichment() -> None:
    plan = plan_answer_key_enrichment(_exam([_unkeyed_single_choice_question()]))

    assert plan.state is AnswerKeyEnrichmentPlanState.ELIGIBLE
    assert tuple(item.item_id for item in plan.unkeyed_items) == ("item-001",)


def test_source_keyed_exam_needs_no_enrichment() -> None:
    plan = plan_answer_key_enrichment(_exam([_keyed_single_choice_question()]))

    assert plan.state is AnswerKeyEnrichmentPlanState.NOT_NEEDED
    assert plan.unkeyed_items == ()


def test_manual_marking_items_do_not_block_supported_unkeyed_items() -> None:
    exam = _exam([_unkeyed_single_choice_question(), _open_ended_question()])

    plan = plan_answer_key_enrichment(exam)

    assert plan.state is AnswerKeyEnrichmentPlanState.ELIGIBLE
    assert tuple(item.item_id for item in plan.unkeyed_items) == ("item-001",)
    assert {(follow_up.item_id, follow_up.reason) for follow_up in exam.manual_follow_ups} == {
        ("item-001", DigiExamIrManualFollowUpReason.MANUAL_ANSWER_KEY_REQUIRED),
        ("item-002", DigiExamIrManualFollowUpReason.MANUAL_MARKING_REQUIRED),
    }


def test_candidate_plan_builds_one_luna_request_per_unkeyed_item() -> None:
    exam = _exam([_unkeyed_single_choice_question()])
    plan = plan_answer_key_enrichment(exam)

    candidates = plan_answer_key_candidates(
        job_id="job-001",
        items=plan.unkeyed_items,
        profile=_profile(),
    )

    assert len(candidates) == 1
    request = candidates[0].request
    assert request.item_id == "item-001"
    assert request.prompt_template_version == "digiexam_choice_answer_key_prompt_v1"
    assert request.output_spec.schema_name == "digiexam_choice_answer_key_decision_v1"
    assert request.output_spec.json_schema["required"] == ["correct_alternative_ids"]
    assert request.max_output_tokens == 4_096
    assert request.estimated_input_tokens == (
        estimate_prompt_tokens(request.system_prompt) + estimate_prompt_tokens(request.user_payload)
    )
    assert '"choice_value":"1"' in request.user_payload


def test_choice_decision_decodes_into_overlay_manual_key() -> None:
    exam = _exam([_unkeyed_single_choice_question()])

    key = manual_answer_key_from_model_content(
        item=exam.items[0],
        content={"correct_alternative_ids": [2]},
    )

    assert key is not None
    assert key.kind == "choice"
    assert key.correct_alternative_ids == (2,)


@pytest.mark.parametrize(
    "content",
    [
        {"correct_alternative_ids": []},
        {"correct_alternative_ids": [9]},
        {"correct_alternative_ids": [1, 1]},
        {"correct_alternative_ids": [1, 2]},
        {"correct_alternative_ids": ["1"]},
        {},
    ],
)
def test_invalid_choice_decisions_yield_no_proposal(content: dict[str, JsonValue]) -> None:
    exam = _exam([_unkeyed_single_choice_question()])

    assert manual_answer_key_from_model_content(item=exam.items[0], content=content) is None


def test_machine_proposed_overlay_completes_unkeyed_exam_with_machine_provenance() -> None:
    exam = _exam([_unkeyed_single_choice_question()])
    key = manual_answer_key_from_model_content(
        item=exam.items[0],
        content={"correct_alternative_ids": [2]},
    )
    assert key is not None
    overlay = build_machine_proposed_overlay(
        source_file_sha256="sha256:file",
        source_ir_sha256="sha256:ir",
        proposals=((exam.items[0], key),),
    )

    result = parse_and_apply_digiexam_ingestion_overlay(
        overlay_bytes=overlay_json_bytes(overlay),
        source_file_sha256="sha256:file",
        source_ir_sha256="sha256:ir",
        source_exam=exam,
        applied_key_provenance=DigiExamAnswerKeyProvenance.MACHINE_PROPOSED_KEY,
    )

    effective = result.effective_exam_for_rendering
    assert exam.items[0].answer_key.provenance == DigiExamAnswerKeyProvenance.ABSENT
    assert effective.items[0].answer_key.provenance == (
        DigiExamAnswerKeyProvenance.MACHINE_PROPOSED_KEY
    )
    assert effective.items[0].answer_key.correct_alternative_ids == (2,)
    assert effective.manual_follow_ups == ()
    report_item = result.effective_exam_report.items[0]
    assert report_item.effective_answer_key is not None
    assert report_item.effective_answer_key.provenance == "machine_proposed"


def test_machine_proposed_overlay_preserves_manual_marking_follow_up() -> None:
    exam = _exam([_unkeyed_single_choice_question(), _open_ended_question()])
    key = manual_answer_key_from_model_content(
        item=exam.items[0],
        content={"correct_alternative_ids": [2]},
    )
    assert key is not None
    overlay = build_machine_proposed_overlay(
        source_file_sha256="sha256:file",
        source_ir_sha256="sha256:ir",
        proposals=((exam.items[0], key),),
    )

    result = parse_and_apply_digiexam_ingestion_overlay(
        overlay_bytes=overlay_json_bytes(overlay),
        source_file_sha256="sha256:file",
        source_ir_sha256="sha256:ir",
        source_exam=exam,
        applied_key_provenance=DigiExamAnswerKeyProvenance.MACHINE_PROPOSED_KEY,
    )

    effective = result.effective_exam_for_rendering
    assert effective.items[0].answer_key.provenance == (
        DigiExamAnswerKeyProvenance.MACHINE_PROPOSED_KEY
    )
    assert effective.items[1].answer_key.provenance == DigiExamAnswerKeyProvenance.NOT_APPLICABLE
    assert tuple(
        (follow_up.item_id, follow_up.reason) for follow_up in effective.manual_follow_ups
    ) == (("item-002", DigiExamIrManualFollowUpReason.MANUAL_MARKING_REQUIRED),)
    adapter_result = build_examnet_qti_items_from_digiexam_ir(effective)
    assert adapter_result.manual_follow_ups == ()
    qti_plan = build_examnet_qti_package_plan(
        package_name="mixed-exam",
        items=adapter_result.items,
    )
    assert qti_plan.status is ExamNetQtiPackageStatus.PASSED
    assert build_digiexam_examnet_pdf_document(effective).status is (
        DigiExamExamNetPdfStatus.SUCCESS
    )


def test_teacher_overlay_provenance_stays_the_unchanged_default() -> None:
    exam = _exam([_unkeyed_single_choice_question()])
    key = manual_answer_key_from_model_content(
        item=exam.items[0],
        content={"correct_alternative_ids": [2]},
    )
    assert key is not None
    overlay = build_machine_proposed_overlay(
        source_file_sha256="sha256:file",
        source_ir_sha256="sha256:ir",
        proposals=((exam.items[0], key),),
    )

    result = parse_and_apply_digiexam_ingestion_overlay(
        overlay_bytes=overlay_json_bytes(overlay),
        source_file_sha256="sha256:file",
        source_ir_sha256="sha256:ir",
        source_exam=exam,
    )

    assert result.effective_exam_for_rendering.items[0].answer_key.provenance == (
        DigiExamAnswerKeyProvenance.MANUAL_TEACHER_KEY
    )
