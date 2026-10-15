"""QTI 3.0 package planning for Exam.net-oriented artifacts.

Purpose:
    Build deterministic, filesystem-free QTI package plans including item XML,
    IMS manifest XML, image resources, proof state, and manual follow-up.

Relationships:
    - Consumes `domain.examnet_qti_contracts` items.
    - Uses `domain.examnet_qti_item_admissibility` to block unrepresentable items.
    - Uses `domain.examnet_qti_xml` for assessment item serialization.
    - Uses `domain.examnet_qti_manifest` for IMS manifest serialization.
    - Feeds infrastructure zip writers and validation-report assembly.
"""

from __future__ import annotations

import hashlib
import re
from typing import Literal

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_assessment_test_xml import (
    EXAMNET_QTI_ASSESSMENT_TEST_PATH,
    serialize_qti_assessment_test,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    EXAMNET_QTI_AUTOMATIC_PROFILE_ID,
    EXAMNET_QTI_GENERATOR_VERSION,
    EXAMNET_QTI_MANUAL_UNKEYED_PROFILE_ID,
    EXAMNET_QTI_PACKAGE_SCHEMA_VERSION,
    EXAMNET_QTI_VERSION,
    ExamNetQtiEvaluationMode,
    ExamNetQtiExamNetProofStatus,
    ExamNetQtiImageResource,
    ExamNetQtiInteractionType,
    ExamNetQtiItem,
    ExamNetQtiManualFollowUp,
    ExamNetQtiPackageFile,
    ExamNetQtiPackagePlan,
    ExamNetQtiPackageStatus,
    ExamNetQtiTargetSupportStatus,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_item_admissibility import (
    IMAGE_MEDIA_TYPES,
    blocking_errors,
    manual_follow_ups,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_item_xml import (
    serialize_qti_assessment_item,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_manifest import (
    serialize_qti_manifest,
)


def build_examnet_qti_package_plan(
    *,
    package_name: str,
    items: tuple[ExamNetQtiItem, ...],
    assessment_title: str | None = None,
) -> ExamNetQtiPackagePlan:
    """Build a deterministic QTI package plan for the supplied items.

    ``assessment_title`` names the assessment test and its section; a missing or
    blank value falls back to ``package_name``.
    """

    follow_ups = manual_follow_ups(items)
    errors = blocking_errors(items)
    if errors:
        return _blocked_plan(
            package_name=package_name,
            items=items,
            manual_follow_ups=follow_ups,
            warnings=errors,
        )

    ordered_items = tuple(sorted(items, key=lambda value: value.sequence))
    item_files: list[ExamNetQtiPackageFile] = []
    image_files_by_item_id: dict[str, tuple[ExamNetQtiPackageFile, ...]] = {}
    for item in ordered_items:
        image_files = tuple(_image_file(item, image) for image in item.image_resources)
        image_paths = tuple(f"../{image.relative_path}" for image in image_files)
        item_xml = serialize_qti_assessment_item(item, image_paths=image_paths)
        item_files.append(
            _package_file(
                relative_path=_item_xml_path(item),
                content_type="application/xml",
                payload=item_xml,
            )
        )
        image_files_by_item_id[item.item_id] = image_files

    assessment_file = _assessment_test_file(
        title=(assessment_title or "").strip() or package_name, items=ordered_items
    )
    manifest = _package_file(
        relative_path="imsmanifest.xml",
        content_type="application/xml",
        payload=serialize_qti_manifest(
            item_files=tuple(item_files),
            image_files_by_item_id=image_files_by_item_id,
        ),
    )
    files = tuple(
        sorted(
            (manifest, assessment_file, *item_files, *_all_image_files(image_files_by_item_id)),
            key=_file_sort_key,
        )
    )
    return ExamNetQtiPackagePlan(
        schema_version=EXAMNET_QTI_PACKAGE_SCHEMA_VERSION,
        generator_version=EXAMNET_QTI_GENERATOR_VERSION,
        qti_version=EXAMNET_QTI_VERSION,
        profile_id=_profile_id(items),
        package_name=package_name,
        status=ExamNetQtiPackageStatus.PASSED,
        target_support_status=_target_support_status(items),
        examnet_proof_status=_proof_status(items),
        items=items,
        files=files,
        manual_follow_ups=follow_ups,
        warnings=(),
    )


def build_blocked_examnet_qti_package_plan(
    *,
    package_name: str,
    items: tuple[ExamNetQtiItem, ...],
    manual_follow_ups: tuple[ExamNetQtiManualFollowUp, ...],
    warnings: tuple[str, ...],
) -> ExamNetQtiPackagePlan:
    """Build a blocked QTI plan when source items cannot all be represented."""

    return _blocked_plan(
        package_name=package_name,
        items=items,
        manual_follow_ups=manual_follow_ups,
        warnings=warnings,
    )


def _blocked_plan(
    *,
    package_name: str,
    items: tuple[ExamNetQtiItem, ...],
    manual_follow_ups: tuple[ExamNetQtiManualFollowUp, ...],
    warnings: tuple[str, ...],
) -> ExamNetQtiPackagePlan:
    return ExamNetQtiPackagePlan(
        schema_version=EXAMNET_QTI_PACKAGE_SCHEMA_VERSION,
        generator_version=EXAMNET_QTI_GENERATOR_VERSION,
        qti_version=EXAMNET_QTI_VERSION,
        profile_id=_profile_id(items),
        package_name=package_name,
        status=ExamNetQtiPackageStatus.BLOCKED,
        target_support_status=_target_support_status(items),
        examnet_proof_status=_proof_status(items),
        items=items,
        files=(),
        manual_follow_ups=manual_follow_ups,
        warnings=warnings,
    )


def _item_xml_path(item: ExamNetQtiItem) -> str:
    return f"items/{item.item_id}.xml"


def _assessment_test_file(
    *,
    title: str,
    items: tuple[ExamNetQtiItem, ...],
) -> ExamNetQtiPackageFile:
    payload = serialize_qti_assessment_test(
        title=title,
        item_ids=tuple(item.item_id for item in items),
    )
    return _package_file(
        relative_path=EXAMNET_QTI_ASSESSMENT_TEST_PATH,
        content_type="application/xml",
        payload=payload,
    )


def _image_file(item: ExamNetQtiItem, image: ExamNetQtiImageResource) -> ExamNetQtiPackageFile:
    extension = IMAGE_MEDIA_TYPES[image.media_type]
    filename = f"{item.item_id}-{_safe_path_stem(image.asset_id)}{extension}"
    return _package_file(
        relative_path=f"resources/{filename}",
        content_type=image.media_type,
        payload=image.payload,
    )


def _package_file(relative_path: str, content_type: str, payload: bytes) -> ExamNetQtiPackageFile:
    return ExamNetQtiPackageFile(
        relative_path=relative_path,
        content_type=content_type,
        payload=payload,
        sha256=hashlib.sha256(payload).hexdigest(),
    )


def _all_image_files(
    image_files_by_item_id: dict[str, tuple[ExamNetQtiPackageFile, ...]],
) -> tuple[ExamNetQtiPackageFile, ...]:
    return tuple(file for files in image_files_by_item_id.values() for file in files)


def _file_sort_key(file: ExamNetQtiPackageFile) -> tuple[int, str]:
    if file.relative_path == "imsmanifest.xml":
        return (0, "")
    if file.relative_path == EXAMNET_QTI_ASSESSMENT_TEST_PATH:
        return (1, "")
    if file.relative_path.startswith("items/"):
        return (2, file.relative_path)
    return (3, file.relative_path)


def _target_support_status(
    items: tuple[ExamNetQtiItem, ...],
) -> ExamNetQtiTargetSupportStatus:
    if _has_proof_gated_interaction(items):
        return ExamNetQtiTargetSupportStatus.PROOF_GATED
    return ExamNetQtiTargetSupportStatus.VENDOR_REPORTED_MINIMUM


def _profile_id(
    items: tuple[ExamNetQtiItem, ...],
) -> Literal["examnet_qti_3_0_v1", "unkeyed_manual_qti_3_0_v1"]:
    if any(item.evaluation_mode == ExamNetQtiEvaluationMode.MANUAL_UNKEYED for item in items):
        return EXAMNET_QTI_MANUAL_UNKEYED_PROFILE_ID
    return EXAMNET_QTI_AUTOMATIC_PROFILE_ID


def _proof_status(items: tuple[ExamNetQtiItem, ...]) -> ExamNetQtiExamNetProofStatus:
    if _has_proof_gated_interaction(items):
        return ExamNetQtiExamNetProofStatus.NOT_PROVEN
    return ExamNetQtiExamNetProofStatus.VENDOR_REPORTED_UNPROVEN


def _has_proof_gated_interaction(items: tuple[ExamNetQtiItem, ...]) -> bool:
    """Whether any item, or any child of a parent, is a gap fill or a matching."""
    return any(
        leaf.interaction_type
        in {ExamNetQtiInteractionType.GAP_FILL, ExamNetQtiInteractionType.MATCHING}
        for item in items
        for leaf in (item.children or (item,))
    )


def _safe_path_stem(value: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9_-]+", "-", value.strip()).strip("-")
    return safe or "asset"
