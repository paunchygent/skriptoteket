"""Tests for Exam.net QTI package admission and readiness.

Purpose:
    Prove which Exam.net QTI items block or pass package planning (missing
    answer keys, missing gap values, non-positive scores) and how validation
    reports express blocked and failed states, ported from Sir Convert-a-Lot at
    revision 41be61a6.

Relationships:
    - Exercises the exam-conversion QTI item admissibility, package planning,
      and validation report builders.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiChoice,
    ExamNetQtiEvaluationMode,
    ExamNetQtiInteractionType,
    ExamNetQtiItem,
    ExamNetQtiManualFollowUpReason,
    ExamNetQtiPackageStatus,
    ExamNetQtiTextEntryGap,
    ExamNetQtiValidationStatus,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_package import (
    build_examnet_qti_package_plan,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_validation import (
    build_examnet_qti_validation_report,
)
from tests.fixtures.exam_conversion_samples import examnet_qti_manual_unkeyed_samples
from tests.unit.domain.curated_apps.exam_conversion.examnet_qti_test_support import (
    QTI_PACKAGE_WRITER,
    first_manual_follow_up,
    json_string,
    keyed_sample,
    read_report,
    write_sample,
)

pytestmark = pytest.mark.unit


def test_post_missing_choice_key_blocks_qti_package(
    tmp_path: Path,
) -> None:
    samples = {sample.name: sample for sample in examnet_qti_manual_unkeyed_samples()}
    sample_dir = write_sample(samples["unkeyed-multiple-response-preserved"], tmp_path)
    report = read_report(sample_dir / "qti-validation-report.json")

    assert not (sample_dir / "qti-package.zip").exists()
    assert json_string(report, "package_status") == "blocked"
    assert json_string(report, "profile_id") == "examnet_qti_3_0_v1"
    follow_up = first_manual_follow_up(report)
    assert json_string(follow_up, "reason_code") == (
        ExamNetQtiManualFollowUpReason.MANUAL_ANSWER_KEY_REQUIRED
    )
    assert _report_contains_warning(report, "needs one or more correct choices")


def test_post_missing_gap_values_block_qti_package(
    tmp_path: Path,
) -> None:
    samples = {sample.name: sample for sample in examnet_qti_manual_unkeyed_samples()}
    sample_dir = write_sample(samples["manual-gap-fill-preserved-as-free-text"], tmp_path)
    report = read_report(sample_dir / "qti-validation-report.json")

    assert not (sample_dir / "qti-package.zip").exists()
    assert json_string(report, "package_status") == "blocked"
    follow_up = first_manual_follow_up(report)
    assert json_string(follow_up, "reason_code") == (
        ExamNetQtiManualFollowUpReason.MANUAL_ANSWER_KEY_REQUIRED
    )
    assert _report_contains_warning(report, "accepted values for every gap")


def test_validation_reports_cover_blocked_and_failed_states() -> None:
    blocked_plan = build_examnet_qti_package_plan(
        package_name="blocked",
        items=(
            ExamNetQtiItem(
                item_id="item_001",
                sequence=1,
                title="Missing key",
                interaction_type=ExamNetQtiInteractionType.SINGLE_CHOICE,
                prompt_lines=("Choose one.",),
                max_score=1,
                choices=(
                    ExamNetQtiChoice("choice_001", "Alpha"),
                    ExamNetQtiChoice("choice_002", "Beta"),
                ),
            ),
        ),
    )
    blocked_report = build_examnet_qti_validation_report(
        plan=blocked_plan,
        package_filename="qti-package.zip",
        package_bytes=None,
    )

    assert blocked_plan.status == ExamNetQtiPackageStatus.BLOCKED
    assert blocked_report.package_status == ExamNetQtiPackageStatus.BLOCKED
    assert blocked_report.validator_results[0].status == ExamNetQtiValidationStatus.BLOCKED

    passed_plan = build_examnet_qti_package_plan(
        package_name="failed-validation",
        items=(keyed_sample("free-text").items[0],),
    )
    failed_report = build_examnet_qti_validation_report(
        plan=passed_plan,
        package_filename="qti-package.zip",
        package_bytes=b"not a zip",
    )

    assert failed_report.package_status == ExamNetQtiPackageStatus.FAILED
    assert failed_report.validator_results[0].status == ExamNetQtiValidationStatus.FAILED
    assert "not a readable zip" in failed_report.errors[0]


def test_manual_unkeyed_choice_plan_passes_where_automatic_choice_blocks() -> None:
    item = ExamNetQtiItem(
        item_id="item_001",
        sequence=1,
        title="Missing key",
        interaction_type=ExamNetQtiInteractionType.SINGLE_CHOICE,
        prompt_lines=("Choose one.",),
        max_score=1,
        choices=(
            ExamNetQtiChoice("choice_001", "Alpha"),
            ExamNetQtiChoice("choice_002", "Beta"),
        ),
    )
    automatic_plan = build_examnet_qti_package_plan(
        package_name="automatic-blocked",
        items=(item,),
    )
    manual_plan = build_examnet_qti_package_plan(
        package_name="manual-passed",
        items=(
            ExamNetQtiItem(
                item_id=item.item_id,
                sequence=item.sequence,
                title=item.title,
                interaction_type=item.interaction_type,
                prompt_lines=item.prompt_lines,
                max_score=item.max_score,
                evaluation_mode=ExamNetQtiEvaluationMode.MANUAL_UNKEYED,
                choices=item.choices,
            ),
        ),
    )

    assert automatic_plan.status == ExamNetQtiPackageStatus.BLOCKED
    assert manual_plan.status == ExamNetQtiPackageStatus.PASSED


def test_gap_fill_plan_blocks_when_any_gap_lacks_accepted_values() -> None:
    plan = build_examnet_qti_package_plan(
        package_name="missing-gap-key",
        items=(
            ExamNetQtiItem(
                item_id="item_001",
                sequence=1,
                title="Lucktext",
                interaction_type=ExamNetQtiInteractionType.GAP_FILL,
                prompt_lines=("Fyll i _____.",),
                max_score=1,
                text_entry_gaps=(
                    ExamNetQtiTextEntryGap(
                        response_identifier="RESPONSE_gap_001",
                        label="Lucka 1",
                        accepted_values=(),
                    ),
                ),
            ),
        ),
    )

    assert plan.status == ExamNetQtiPackageStatus.BLOCKED
    assert plan.manual_follow_ups[0].reason_code == (
        ExamNetQtiManualFollowUpReason.MANUAL_ANSWER_KEY_REQUIRED
    )
    assert "accepted values for every gap" in plan.warnings[0]


def test_keyed_automatic_item_with_zero_score_passes_plan() -> None:
    plan = build_examnet_qti_package_plan(
        package_name="zero-score",
        items=(
            ExamNetQtiItem(
                item_id="item_001",
                sequence=1,
                title="Zero score",
                interaction_type=ExamNetQtiInteractionType.SINGLE_CHOICE,
                prompt_lines=("Choose one.",),
                max_score=0,
                choices=(
                    ExamNetQtiChoice("choice_001", "Alpha"),
                    ExamNetQtiChoice("choice_002", "Beta"),
                ),
                correct_choice_identifiers=("choice_001",),
            ),
        ),
    )

    assert plan.status == ExamNetQtiPackageStatus.PASSED
    assert plan.warnings == ()
    assert plan.manual_follow_ups == ()


def test_blocked_plan_refuses_package_bytes_but_still_reports() -> None:
    samples = {sample.name: sample for sample in examnet_qti_manual_unkeyed_samples()}
    sample = samples["unkeyed-multiple-response-preserved"]

    plan = build_examnet_qti_package_plan(package_name=sample.name, items=sample.items)

    assert plan.status == ExamNetQtiPackageStatus.BLOCKED
    with pytest.raises(ValueError, match="passed QTI package plans"):
        QTI_PACKAGE_WRITER.build_package_bytes(plan)
    report_bytes = QTI_PACKAGE_WRITER.build_validation_report_bytes(
        plan=plan,
        package_filename=sample.package_filename,
        package_bytes=None,
    )
    report = json.loads(report_bytes)
    assert report["package_status"] == "blocked"


def _report_contains_warning(report: dict[str, object], expected_text: str) -> bool:
    value = report["warnings"]
    assert isinstance(value, list)
    return any(isinstance(warning, str) and expected_text in warning for warning in value)
