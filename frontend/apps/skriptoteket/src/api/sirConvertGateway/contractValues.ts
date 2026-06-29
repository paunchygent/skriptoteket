/**
 * Sir Convert DigiExam contract values.
 *
 * Purpose:
 *   Centralize non-version DigiExam migration literals that must line up with
 *   Sir Convert's generated OpenAPI contract.
 *
 * Relationships:
 *   - `schemaVersions.ts` owns schema-version constants.
 *   - `types.ts` derives unions from `sirConvertOpenapi.d.ts`.
 *   - Gateway builders, parsers, fixtures, and UI projections import these
 *     constants instead of repeating raw contract strings.
 */

import type {
  DigiExamItemType,
  DigiExamMigrationArtifactKey,
  DigiExamMigrationTarget,
  DigiExamTargetReadiness,
  SirConvertArtifactAvailability,
  SirConvertBundleStatus,
} from "./types";

export const DIGIEXAM_SOURCE_FORMAT = "digiexam_dxe" as const;
export const DIGIEXAM_MIGRATION_OUTPUT_FORMAT = "examnet_migration_bundle" as const;
export const DIGIEXAM_MIGRATION_ROUTE_KEY =
  "digiexam_dxe_to_examnet_migration_bundle" as const;

export const DIGIEXAM_TARGET_EXAMNET_PDF =
  "examnet_pdf" as const satisfies DigiExamMigrationTarget;
export const DIGIEXAM_TARGET_QTI_PACKAGE =
  "qti_package" as const satisfies DigiExamMigrationTarget;
export const DIGIEXAM_MIGRATION_TARGETS = [
  DIGIEXAM_TARGET_EXAMNET_PDF,
  DIGIEXAM_TARGET_QTI_PACKAGE,
] as const satisfies readonly DigiExamMigrationTarget[];

export const DIGIEXAM_ARTIFACT_IR_JSON =
  "ir_json" as const satisfies DigiExamMigrationArtifactKey;
export const DIGIEXAM_ARTIFACT_EFFECTIVE_IR_JSON =
  "effective_ir_json" as const satisfies DigiExamMigrationArtifactKey;
export const DIGIEXAM_ARTIFACT_MIGRATION_MANIFEST =
  "migration_manifest" as const satisfies DigiExamMigrationArtifactKey;
export const DIGIEXAM_ARTIFACT_TARGET_READINESS_REPORT =
  "target_readiness_report" as const satisfies DigiExamMigrationArtifactKey;
export const DIGIEXAM_ARTIFACT_ANSWER_KEY_COMPLETION_REPORT =
  "answer_key_completion_report" as const satisfies DigiExamMigrationArtifactKey;
export const DIGIEXAM_ARTIFACT_ANSWER_KEY_REVIEW_STATE_REPORT =
  "answer_key_review_state_report" as const satisfies DigiExamMigrationArtifactKey;
export const DIGIEXAM_ARTIFACT_MANUAL_FOLLOW_UP_REPORT =
  "manual_follow_up_report" as const satisfies DigiExamMigrationArtifactKey;
export const DIGIEXAM_ARTIFACT_WARNINGS_REPORT =
  "warnings_report" as const satisfies DigiExamMigrationArtifactKey;

export const DIGIEXAM_RESULT_PDF_USAGE_CORRECT_MACHINE_MARKED =
  "correct_machine_marked_answers_only" as const;
export const DIGIEXAM_COMPLETION_MODE_SOURCE_EVIDENCE_ONLY =
  "source_evidence_only" as const;
export const DIGIEXAM_COMPLETION_MODE_SUGGEST_MISSING_MACHINE_MARKED =
  "local_llm_suggest_missing_machine_marked" as const;
export const DIGIEXAM_COMPLETION_MODE_APPLY_REVIEWED_MISSING_MACHINE_MARKED =
  "local_llm_apply_missing_machine_marked_with_review" as const;
export const DIGIEXAM_REMOTE_PROVIDER_POLICY_FORBIDDEN = "forbidden" as const;
export const DIGIEXAM_MANUAL_FOLLOW_UP_POLICY_ITEM_ADDRESSABLE =
  "emit_item_addressable_report" as const;
export const DIGIEXAM_INGESTION_OVERLAY_POLICY_NONE = "none" as const;
export const DIGIEXAM_INGESTION_OVERLAY_POLICY_APPLY_TEACHER =
  "apply_teacher_overlay" as const;
export const DIGIEXAM_INGESTION_OVERLAY_FILENAME = "digiexam-ingestion-overlay.json";
export const DIGIEXAM_MANUAL_FOLLOW_UP_MANUAL_ANSWER_KEY_REQUIRED =
  "manual_answer_key_required" as const;
export const DIGIEXAM_MANUAL_FOLLOW_UP_MANUAL_MARKING_REQUIRED =
  "manual_marking_required" as const;
export const DIGIEXAM_MANUAL_FOLLOW_UP_UNSUPPORTED_ITEM_TYPE =
  "unsupported_item_type" as const;
export const DIGIEXAM_MANUAL_FOLLOW_UP_PARSER_WARNING_BLOCKS_RENDERING =
  "parser_warning_blocks_rendering" as const;

export const DIGIEXAM_ITEM_TYPE_OPEN_ENDED = "open_ended" as const satisfies DigiExamItemType;
export const DIGIEXAM_ITEM_TYPE_MULTIPLE_CHOICE =
  "multiple_choice" as const satisfies DigiExamItemType;
export const DIGIEXAM_ITEM_TYPE_SINGLE_CHOICE =
  "single_choice" as const satisfies DigiExamItemType;
export const DIGIEXAM_ITEM_TYPE_MULTIPLE_RESPONSE =
  "multiple_response" as const satisfies DigiExamItemType;
export const DIGIEXAM_ITEM_TYPE_GAP_FILL = "gap_fill" as const satisfies DigiExamItemType;
export const DIGIEXAM_ITEM_TYPE_UNKNOWN = "unknown" as const satisfies DigiExamItemType;
export const DIGIEXAM_ITEM_TYPES = [
  DIGIEXAM_ITEM_TYPE_OPEN_ENDED,
  DIGIEXAM_ITEM_TYPE_MULTIPLE_CHOICE,
  DIGIEXAM_ITEM_TYPE_SINGLE_CHOICE,
  DIGIEXAM_ITEM_TYPE_MULTIPLE_RESPONSE,
  DIGIEXAM_ITEM_TYPE_GAP_FILL,
  DIGIEXAM_ITEM_TYPE_UNKNOWN,
] as const satisfies readonly DigiExamItemType[];

export const SIR_CONVERT_BUNDLE_STATUS_COMPLETE =
  "complete" as const satisfies SirConvertBundleStatus;
export const SIR_CONVERT_BUNDLE_STATUS_PARTIAL =
  "partial" as const satisfies SirConvertBundleStatus;
export const SIR_CONVERT_BUNDLE_STATUS_NEEDS_REVIEW =
  "needs_review" as const satisfies SirConvertBundleStatus;
export const SIR_CONVERT_BUNDLE_STATUS_FAILED =
  "failed" as const satisfies SirConvertBundleStatus;
export const SIR_CONVERT_BUNDLE_STATUSES = [
  SIR_CONVERT_BUNDLE_STATUS_COMPLETE,
  SIR_CONVERT_BUNDLE_STATUS_PARTIAL,
  SIR_CONVERT_BUNDLE_STATUS_NEEDS_REVIEW,
  SIR_CONVERT_BUNDLE_STATUS_FAILED,
] as const satisfies readonly SirConvertBundleStatus[];

export const SIR_CONVERT_ARTIFACT_AVAILABLE =
  "available" as const satisfies SirConvertArtifactAvailability;
export const SIR_CONVERT_ARTIFACT_UNAVAILABLE =
  "unavailable" as const satisfies SirConvertArtifactAvailability;
export const SIR_CONVERT_ARTIFACT_FAILED =
  "failed" as const satisfies SirConvertArtifactAvailability;
export const SIR_CONVERT_ARTIFACT_NOT_REQUESTED =
  "not_requested" as const satisfies SirConvertArtifactAvailability;
export const SIR_CONVERT_ARTIFACT_NOT_IMPLEMENTED =
  "not_implemented" as const satisfies SirConvertArtifactAvailability;
export const SIR_CONVERT_ARTIFACT_NOT_SUPPORTED_BY_EXAMNET =
  "not_supported_by_examnet" as const satisfies SirConvertArtifactAvailability;
export const SIR_CONVERT_ARTIFACT_AVAILABILITIES = [
  SIR_CONVERT_ARTIFACT_AVAILABLE,
  SIR_CONVERT_ARTIFACT_UNAVAILABLE,
  SIR_CONVERT_ARTIFACT_FAILED,
  SIR_CONVERT_ARTIFACT_NOT_REQUESTED,
  SIR_CONVERT_ARTIFACT_NOT_IMPLEMENTED,
  SIR_CONVERT_ARTIFACT_NOT_SUPPORTED_BY_EXAMNET,
] as const satisfies readonly SirConvertArtifactAvailability[];

export const DIGIEXAM_TARGET_READY = "ready" as const satisfies DigiExamTargetReadiness;
export const DIGIEXAM_TARGET_NEEDS_TEACHER_ANSWER_KEY =
  "needs_teacher_answer_key" as const satisfies DigiExamTargetReadiness;
export const DIGIEXAM_TARGET_UNSUPPORTED_TARGET_SHAPE =
  "unsupported_target_shape" as const satisfies DigiExamTargetReadiness;
export const DIGIEXAM_TARGET_VALIDATION_FAILED =
  "target_validation_failed" as const satisfies DigiExamTargetReadiness;
export const DIGIEXAM_TARGET_PROVIDER_UNAVAILABLE =
  "provider_unavailable" as const satisfies DigiExamTargetReadiness;
export const DIGIEXAM_TARGET_NOT_REQUESTED =
  "not_requested" as const satisfies DigiExamTargetReadiness;
export const DIGIEXAM_TARGET_NOT_IMPLEMENTED =
  "not_implemented" as const satisfies DigiExamTargetReadiness;
export const DIGIEXAM_TARGET_READINESS_VALUES = [
  DIGIEXAM_TARGET_READY,
  DIGIEXAM_TARGET_NEEDS_TEACHER_ANSWER_KEY,
  DIGIEXAM_TARGET_UNSUPPORTED_TARGET_SHAPE,
  DIGIEXAM_TARGET_VALIDATION_FAILED,
  DIGIEXAM_TARGET_PROVIDER_UNAVAILABLE,
  DIGIEXAM_TARGET_NOT_REQUESTED,
  DIGIEXAM_TARGET_NOT_IMPLEMENTED,
] as const satisfies readonly DigiExamTargetReadiness[];

export const DIGIEXAM_ANSWER_KEY_REVIEW_STATES = [
  "review_required",
  "review_complete",
  "teacher_modified",
  "validation_required",
] as const;

export const DIGIEXAM_ANSWER_KEY_ORIGINS = [
  "none",
  "source_provided",
  "reviewed_advisory",
  "teacher_authored",
  "teacher_edited_advisory",
  "mixed",
] as const;

export const DIGIEXAM_ANSWER_KEY_REVIEW_REASONS = [
  "source_answer_key_present",
  "advisory_candidate_pending",
  "reviewed_advisory_accepted",
  "teacher_answer_key_present",
  "teacher_edited_advisory_candidate",
  "answer_key_not_applicable",
  "manual_answer_key_required",
  "no_correct_choice_selected",
  "required_gap_accepted_values_missing",
  "unsupported_item_type",
  "unsupported_target_shape",
  "target_validation_failed",
  "provider_unavailable",
  "correction_rejected",
  "stale_source_state",
  "replay_artifact_unavailable",
  "matching_source_state_unavailable",
] as const;
