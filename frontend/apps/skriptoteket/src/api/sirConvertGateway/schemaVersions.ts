/**
 * Sir Convert DigiExam schema-version constants.
 *
 * Purpose:
 *   Keep the SPA's Sir Convert gateway parser, review fixtures, and save
 *   metadata bound to one generated-ready DigiExam migration version surface.
 *
 * Relationships:
 *   - Mirrors Sir Convert's OpenAPI `x-sir-convert-digiexam-schema-versions`
 *     extension.
 *   - Imported by gateway types, parsers, fixtures, and review artifact readers
 *     instead of duplicating schema-version literals.
 */

export const DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION = "digiexam_migration_bundle_v3" as const;
export const DIGIEXAM_INTERMEDIATE_EXAM_SCHEMA_VERSION =
  "digiexam_intermediate_exam_v3" as const;
export const DIGIEXAM_IR_MANIFEST_SCHEMA_VERSION = "digiexam_ir_manifest_v3" as const;
export const DIGIEXAM_EFFECTIVE_EXAM_SCHEMA_VERSION = "digiexam_effective_exam_v2" as const;
export const DIGIEXAM_INGESTION_OVERLAY_SCHEMA_VERSION =
  "digiexam_ingestion_overlay_v2" as const;
export const TARGET_READINESS_REPORT_SCHEMA_VERSION = "target_readiness_report_v1" as const;
export const ANSWER_KEY_COMPLETION_REPORT_SCHEMA_VERSION =
  "answer_key_completion_report_v1" as const;
export const ANSWER_KEY_REVIEW_STATE_SCHEMA_VERSION =
  "digiexam_answer_key_review_state_v1" as const;

export type DigiExamMigrationBundleSchemaVersion =
  typeof DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION;
export type DigiExamIntermediateExamSchemaVersion =
  typeof DIGIEXAM_INTERMEDIATE_EXAM_SCHEMA_VERSION;
export type DigiExamIrManifestSchemaVersion = typeof DIGIEXAM_IR_MANIFEST_SCHEMA_VERSION;
export type DigiExamEffectiveExamSchemaVersion = typeof DIGIEXAM_EFFECTIVE_EXAM_SCHEMA_VERSION;
export type DigiExamIngestionOverlaySchemaVersion =
  typeof DIGIEXAM_INGESTION_OVERLAY_SCHEMA_VERSION;
export type TargetReadinessReportSchemaVersion = typeof TARGET_READINESS_REPORT_SCHEMA_VERSION;
export type AnswerKeyCompletionReportSchemaVersion =
  typeof ANSWER_KEY_COMPLETION_REPORT_SCHEMA_VERSION;
