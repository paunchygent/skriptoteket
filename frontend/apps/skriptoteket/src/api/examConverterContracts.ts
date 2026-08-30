/** Local contracts for Skriptoteket-owned authenticated Exam Converter flows. */

export const DIGIEXAM_SOURCE_FORMAT = "digiexam_dxe" as const;
export const DIGIEXAM_MIGRATION_ROUTE_KEY = "digiexam_dxe_to_examnet_migration_bundle" as const;
export const DIGIEXAM_TARGET_EXAMNET_PDF = "examnet_pdf" as const;
export const DIGIEXAM_TARGET_QTI_PACKAGE = "qti_package" as const;
export const DEFAULT_DIGIEXAM_MIGRATION_TARGETS = [
  DIGIEXAM_TARGET_EXAMNET_PDF,
  DIGIEXAM_TARGET_QTI_PACKAGE,
] as const;
export const DIGIEXAM_ARTIFACT_IR_JSON = "ir_json" as const;
export const DIGIEXAM_ARTIFACT_EFFECTIVE_IR_JSON = "effective_ir_json" as const;
export const DIGIEXAM_ARTIFACT_MIGRATION_MANIFEST = "migration_manifest" as const;
export const DIGIEXAM_ARTIFACT_TARGET_READINESS_REPORT = "target_readiness_report" as const;
export const DIGIEXAM_ARTIFACT_ANSWER_KEY_COMPLETION_REPORT = "answer_key_completion_report" as const;
export const DIGIEXAM_ARTIFACT_ANSWER_KEY_REVIEW_STATE_REPORT = "answer_key_review_state_report" as const;
export const DIGIEXAM_ARTIFACT_MANUAL_FOLLOW_UP_REPORT = "manual_follow_up_report" as const;
export const DIGIEXAM_ARTIFACT_WARNINGS_REPORT = "warnings_report" as const;
export const DIGIEXAM_COMPLETION_MODE_SUGGEST_MISSING_MACHINE_MARKED =
  "local_llm_suggest_missing_machine_marked" as const;
export const DIGIEXAM_ITEM_TYPE_OPEN_ENDED = "open_ended" as const;
export const DIGIEXAM_ITEM_TYPE_MULTIPLE_CHOICE = "multiple_choice" as const;
export const DIGIEXAM_ITEM_TYPE_SINGLE_CHOICE = "single_choice" as const;
export const DIGIEXAM_ITEM_TYPE_MULTIPLE_RESPONSE = "multiple_response" as const;
export const DIGIEXAM_ITEM_TYPE_GAP_FILL = "gap_fill" as const;
export const DIGIEXAM_ITEM_TYPE_UNKNOWN = "unknown" as const;
export const DIGIEXAM_ITEM_TYPES = [
  DIGIEXAM_ITEM_TYPE_OPEN_ENDED,
  DIGIEXAM_ITEM_TYPE_MULTIPLE_CHOICE,
  DIGIEXAM_ITEM_TYPE_SINGLE_CHOICE,
  DIGIEXAM_ITEM_TYPE_MULTIPLE_RESPONSE,
  DIGIEXAM_ITEM_TYPE_GAP_FILL,
  DIGIEXAM_ITEM_TYPE_UNKNOWN,
] as const;
export const EXAM_CONVERTER_BUNDLE_STATUS_COMPLETE = "complete" as const;
export const EXAM_CONVERTER_BUNDLE_STATUS_PARTIAL = "partial" as const;
export const EXAM_CONVERTER_BUNDLE_STATUS_NEEDS_REVIEW = "needs_review" as const;
export const EXAM_CONVERTER_BUNDLE_STATUS_FAILED = "failed" as const;
export const EXAM_CONVERTER_ARTIFACT_AVAILABLE = "available" as const;
export const EXAM_CONVERTER_ARTIFACT_UNAVAILABLE = "unavailable" as const;
export const EXAM_CONVERTER_ARTIFACT_FAILED = "failed" as const;
export const DIGIEXAM_TARGET_READY = "ready" as const;
export const DIGIEXAM_TARGET_NEEDS_TEACHER_ANSWER_KEY = "needs_teacher_answer_key" as const;
export const DIGIEXAM_TARGET_UNSUPPORTED_TARGET_SHAPE = "unsupported_target_shape" as const;
export const DIGIEXAM_TARGET_VALIDATION_FAILED = "target_validation_failed" as const;
export const DIGIEXAM_TARGET_PROVIDER_UNAVAILABLE = "provider_unavailable" as const;
export const DIGIEXAM_TARGET_NOT_REQUESTED = "not_requested" as const;
export const DIGIEXAM_TARGET_NOT_IMPLEMENTED = "not_implemented" as const;
export const DIGIEXAM_ANSWER_KEY_REVIEW_STATES = [
  "review_required", "review_complete", "teacher_modified", "validation_required",
] as const;
export const DIGIEXAM_ANSWER_KEY_ORIGINS = [
  "none", "source_provided", "reviewed_advisory", "teacher_authored", "teacher_edited_advisory", "mixed",
] as const;
export const DIGIEXAM_ANSWER_KEY_REVIEW_REASONS = [
  "source_answer_key_present", "advisory_candidate_pending", "reviewed_advisory_accepted",
  "teacher_answer_key_present", "teacher_edited_advisory_candidate", "answer_key_not_applicable",
  "manual_answer_key_required", "no_correct_choice_selected", "required_gap_accepted_values_missing",
  "unsupported_item_type", "unsupported_target_shape", "target_validation_failed", "provider_unavailable",
  "correction_rejected", "stale_source_state", "replay_artifact_unavailable", "matching_source_state_unavailable",
] as const;
export const DIGIEXAM_MANUAL_FOLLOW_UP_MANUAL_ANSWER_KEY_REQUIRED = "manual_answer_key_required" as const;
export const DIGIEXAM_MANUAL_FOLLOW_UP_MANUAL_MARKING_REQUIRED = "manual_marking_required" as const;
export const DIGIEXAM_MANUAL_FOLLOW_UP_UNSUPPORTED_ITEM_TYPE = "unsupported_item_type" as const;
export const DIGIEXAM_MANUAL_FOLLOW_UP_PARSER_WARNING_BLOCKS_RENDERING = "parser_warning_blocks_rendering" as const;
export const DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION = "digiexam_migration_bundle_v3" as const;
export const DIGIEXAM_INTERMEDIATE_EXAM_SCHEMA_VERSION = "digiexam_intermediate_exam_v3" as const;
export const DIGIEXAM_IR_MANIFEST_SCHEMA_VERSION = "digiexam_ir_manifest_v3" as const;
export const DIGIEXAM_EFFECTIVE_EXAM_SCHEMA_VERSION = "digiexam_effective_exam_v2" as const;
export const TARGET_READINESS_REPORT_SCHEMA_VERSION = "target_readiness_report_v1" as const;
export const ANSWER_KEY_COMPLETION_REPORT_SCHEMA_VERSION = "answer_key_completion_report_v1" as const;
export const ANSWER_KEY_REVIEW_STATE_SCHEMA_VERSION = "digiexam_answer_key_review_state_v1" as const;
export const CORRECTION_REPLAY_ARTIFACT_REFERENCE_SCHEMA_VERSION = "correction_replay_artifact_reference_v1" as const;

export type DigiExamMigrationTarget = (typeof DEFAULT_DIGIEXAM_MIGRATION_TARGETS)[number];
export type DigiExamAnswerKeyCompletionMode =
  | "source_evidence_only"
  | "local_llm_suggest_missing_machine_marked"
  | "local_llm_apply_missing_machine_marked_with_review";
export type DigiExamItemType = (typeof DIGIEXAM_ITEM_TYPES)[number];
export type DigiExamMigrationArtifactKey = string;
export type DigiExamTargetReadiness =
  | "ready" | "needs_teacher_answer_key" | "unsupported_target_shape" | "target_validation_failed"
  | "provider_unavailable" | "not_requested" | "not_implemented";
export type ExamConverterJobStatus =
  | "submitted" | "queued" | "running" | "processing" | "succeeded" | "failed" | "canceled" | "cancelled";
export type ExamConverterBundleStatus = "complete" | "partial" | "needs_review" | "failed";
export type ExamConverterArtifactAvailability =
  | "available" | "unavailable" | "failed" | "not_requested" | "not_implemented" | "not_supported_by_examnet";
type AnswerKeyProvenance = "absent" | "source_provided" | "teacher_provided" | "reviewed" | "mixed";
type ExamAuthoringChoice = { choice_id: string; order: number; source_id?: string | null; text: string };
type ExamAuthoringChoiceInteraction = {
  answer_key: { correct_choice_ids: string[]; provenance: AnswerKeyProvenance };
  choices: ExamAuthoringChoice[];
  interaction_id: string;
  interaction_kind: "single_choice" | "multiple_choice" | "multiple_response";
  max_correct_choices: number;
  min_correct_choices: number;
};
type ExamAuthoringGapInteraction = {
  answer_key: {
    accepted_values: { gap_id: string; provenance: AnswerKeyProvenance; value: string }[];
    provenance: AnswerKeyProvenance;
  };
  gaps: { display_order: number; gap_id: string; required_for_auto_evaluation: boolean }[];
  interaction_id: string;
  normalization_profile: string;
};
type DigiExamOverlayManualAnswerKey =
  | { correct_alternative_ids: number[]; kind: "choice" }
  | { gap_answers: { accepted_values: string[]; gap_id: string }[]; kind: "gap_fill" };
type DigiExamOverlayItemPatch =
  | { alternative_overrides: { alternative_id: number; text: string }[]; kind: "choice"; prompt_html: string | null; prompt_lines: string[] | null; title: string | null }
  | { kind: "gap_fill"; prompt_html: string | null; prompt_lines: string[] | null; title: string | null };
type DigiExamOverlayReviewedCompletionAnswerKey = {
  answer_payload:
    | { correct_alternative_ids: number[]; kind: "choice" }
    | { gap_answers: { accepted_values: string[]; gap_id: string }[]; kind: "gap_fill" };
  candidate_lineage: Omit<DigiExamEffectiveAnswerKeyLineage, "review_decision_id" | "review_outcome">;
  kind: "choice" | "gap_fill";
  review_decision_id: string;
  review_outcome: "accepted_unchanged" | "teacher_edited";
};
export type DigiExamIngestionOverlay = {
  schema_version: "digiexam_ingestion_overlay_v2";
  source_binding: { source_file_sha256: string; source_ir_sha256: string };
  items: {
    effective_item_patch: DigiExamOverlayItemPatch | null;
    item_id: string;
    item_type: DigiExamItemType;
    manual_answer_key: DigiExamOverlayManualAnswerKey | null;
    point_correction: DigiExamOverlayPointCorrection | null;
    reviewed_completion_answer_key: DigiExamOverlayReviewedCompletionAnswerKey | null;
    sequence: number;
    source_item_fingerprint: string;
  }[];
};
export type DigiExamOverlayPointCorrection = { kind: "item_points"; max_score: number };
type DigiExamEffectiveAnswerKeyLineage = {
  candidate_id: string; candidate_payload_digest: string; completion_report_sha256: string;
  prompt_template_version: string; provider_profile_id: string; review_decision_id: string;
  review_outcome: "accepted_unchanged" | "teacher_edited"; schema_name: string;
  schema_version: string; validation_state: "valid";
};
type ExamAuthoringCandidateLineage = Omit<
  DigiExamEffectiveAnswerKeyLineage,
  "review_decision_id" | "review_outcome"
>;
export type DigiExamEffectiveAnswerKey = {
  correct_alternative_ids?: number[];
  correct_gap_answers?: { gap_id: string; value: string }[];
  lineage: DigiExamEffectiveAnswerKeyLineage | null;
  provenance: string;
};
export type DigiExamEffectivePointCorrection = { effective_max_score: number; kind: "item_points"; source_item_fingerprint: string; source_max_score: number | null };
export type DigiExamEffectiveExam = {
  answer_key_completion_report_sha256: string | null;
  ingestion_overlay_sha256: string | null;
  items: { applied_overlay_entry_ids?: string[]; effective_answer_key: DigiExamEffectiveAnswerKey | null; effective_item_patch: { changed_fields?: string[]; patched_alternative_ids?: number[]; patched_gap_ids?: string[] } | null; effective_point_correction: DigiExamEffectivePointCorrection | null; item_id: string; item_type: string; sequence: number; source_item_fingerprint: string }[];
  schema_version: typeof DIGIEXAM_EFFECTIVE_EXAM_SCHEMA_VERSION;
  source_file_sha256: string;
  source_ir_schema_version: typeof DIGIEXAM_INTERMEDIATE_EXAM_SCHEMA_VERSION;
  source_ir_sha256: string;
};
export type DigiExamAnswerKeyCompletionReportItem = {
  answer_payload: Record<string, unknown> | null; backend_failure_code: string | null;
  backend_status: string; candidate_id: string | null; candidate_payload_digest: string | null;
  decision_state: "suggested" | "manual_follow_up_required" | "skipped"; item_id: string;
  item_type: string; model_profile: string | null; prompt_template_version: string | null;
  provider_profile_id: string | null; schema_name: string | null; schema_version: string | null;
  sequence: number; validation_state: "valid" | "invalid" | "manual_follow_up_required" | "skipped";
};
export type DigiExamAnswerKeyCompletionReport = { completion_mode: typeof DIGIEXAM_COMPLETION_MODE_SUGGEST_MISSING_MACHINE_MARKED; items: DigiExamAnswerKeyCompletionReportItem[]; job_id: string; provider_lineage: Record<string, unknown> | null; schema_version: typeof ANSWER_KEY_COMPLETION_REPORT_SCHEMA_VERSION };
export type DigiExamAnswerKeyReviewReplayArtifactReference = { artifact_key: string; artifact_set_id: string; content_sha256: string; correction_payload_digest: string; created_at: string; job_id: string; replay_profile_version: string; request_id: string; schema_version: typeof CORRECTION_REPLAY_ARTIFACT_REFERENCE_SCHEMA_VERSION; source_binding_digest: string; source_state_sha256: string; target: DigiExamMigrationTarget; target_set_digest: string };
type DigiExamAnswerKeyReviewProvenanceDetail = { candidate_id: string; candidate_payload_digest: string; completion_report_sha256: string; prompt_template_version: string; provider_profile_id: string; schema_name: string; schema_version: string; validation_state: "valid" };
export type DigiExamAnswerKeyReviewStateItem = { choice_ids: string[]; choice_interaction_ids: string[]; correction_affordances: string[]; current_key_origin: (typeof DIGIEXAM_ANSWER_KEY_ORIGINS)[number]; gap_ids: string[]; gap_interaction_ids: string[]; item_id: string; item_type: string; message_key: string; provenance_detail: DigiExamAnswerKeyReviewProvenanceDetail | null; reasons: (typeof DIGIEXAM_ANSWER_KEY_REVIEW_REASONS)[number][]; replay_artifact_references: DigiExamAnswerKeyReviewReplayArtifactReference[]; review_state: (typeof DIGIEXAM_ANSWER_KEY_REVIEW_STATES)[number]; sequence: number; source_item_fingerprint: string | null };
export type DigiExamAnswerKeyReviewState = { items: DigiExamAnswerKeyReviewStateItem[]; schema_version: typeof ANSWER_KEY_REVIEW_STATE_SCHEMA_VERSION };
export type DigiExamTargetReadinessRow = { target: string; readiness: DigiExamTargetReadiness; export_enabled: boolean; artifact_key: string | null; reason_code: string; teacher_action: string; retryable: boolean; message_key: string; item_id: string | null; sequence: number | null; source_item_fingerprint: string | null };
export type DigiExamTargetReadinessReport = { schema_version: typeof TARGET_READINESS_REPORT_SCHEMA_VERSION; job_id: string; source_ir_sha256: string; effective_exam_sha256: string; targets: DigiExamTargetReadinessRow[] };
export type DigiExamMigrationSubmitParams = { file: File; advisoryRetryAttempt?: number | null; artifactLanguage?: string; completionMode?: DigiExamAnswerKeyCompletionMode; correlationId?: string | null; ingestionOverlay?: DigiExamIngestionOverlay | null; targets?: DigiExamMigrationTarget[]; waitSeconds?: number };
export type ExamConverterJob = { jobId: string; status: ExamConverterJobStatus };
export type ExamConverterTerminalResult = { job: ExamConverterJob; artifact: { filename: string; content_type: string; sha256: string | null; size_bytes: number | null }; conversion_metadata: { route_key: string; bundle_schema_version: string; bundle_status: ExamConverterBundleStatus; source_sha256: string | null; target_readiness_report_artifact_key: typeof DIGIEXAM_ARTIFACT_TARGET_READINESS_REPORT | null; manual_follow_up_required: boolean; warning_count: number; artifact_count: number } };
export type ExamConverterArtifactEntry = { artifact_key: string; filename: string; content_type: string; availability: ExamConverterArtifactAvailability; size_bytes: number | null; sha256: string | null; download_path?: string; unavailable_code?: string; depends_on?: string };
export type ExamConverterArtifactManifest = { schema_version: typeof DIGIEXAM_MIGRATION_BUNDLE_SCHEMA_VERSION; job_id: string; source: { filename: string; sha256: string; format: typeof DIGIEXAM_SOURCE_FORMAT }; bundle_status: ExamConverterBundleStatus; artifacts: ExamConverterArtifactEntry[]; manual_follow_up: { required: boolean; artifact_key: string; count: number } | null; warnings: { artifact_key: string; count: number } | null; readiness: { artifact_key: typeof DIGIEXAM_ARTIFACT_TARGET_READINESS_REPORT; exportable_targets: string[]; review_required: boolean }; source_binding: { source_ir_schema_version: typeof DIGIEXAM_INTERMEDIATE_EXAM_SCHEMA_VERSION; source_ir_sha256: string; effective_exam_schema_version: string; effective_exam_sha256: string } };
export type ExamConverterArtifactBlob = { blob: Blob; contentType: string | null; filename: string | null; artifactKey: string };
export type ExamConverterSavedUserFile = { source_artifact_id: string; vault_artifact: { bytes: number; created_at: string; file_id: string; name: string } };
export type ExamAuthoringCorrectionSourceItem = { choice_interactions: ExamAuthoringChoiceInteraction[]; gap_open_cloze_interactions: ExamAuthoringGapInteraction[]; item_id: string; item_type: string; matching_interactions: Record<string, unknown>[]; max_score?: number | null; prompt_html?: string | null; prompt_lines: string[]; sequence: number; source_item_fingerprint?: string | null; title?: string | null };
export type ExamAuthoringCorrectionSourceStateIssueResult = { schema_version: "exam_authoring_correction_source_state_issue_result_v1"; source_binding: { source_authoring_schema_version: string; source_bundle_id: string; source_file_sha256: string; source_state_sha256: string; source_state_signature: string }; source_authoring_state: { schema_version: string; source_authoring_schema_version: string; source_state_sha256: string; items: ExamAuthoringCorrectionSourceItem[] } };
export type ExamAuthoringCorrectionsApplyRequest = { corrections: ExamAuthoringNonMatchingCorrectionEntry[]; requested_targets: DigiExamMigrationTarget[]; source_binding: ExamAuthoringCorrectionSourceStateIssueResult["source_binding"]; source_authoring_state: ExamAuthoringCorrectionSourceStateIssueResult["source_authoring_state"]; schema_version: "exam_authoring_corrections_apply_request_v1"; request_id: string };
type ExamAuthoringCorrectionEntryBase = { entry_id: string; item_id: string; item_type: string; sequence: number; source_item_fingerprint: string | null };
export type ExamAuthoringNonMatchingCorrectionEntry = ExamAuthoringCorrectionEntryBase & (
  | { kind: "point_correction"; max_score: number }
  | { kind: "item_text_patch"; patches: { field: string; value: string }[] }
  | { candidate_lineage: ExamAuthoringCandidateLineage | null; correct_choice_ids: string[]; interaction_id: string; kind: "manual_choice_answer_key"; submission_origin: "teacher_authored" | "teacher_edited_advisory_candidate" | "accepted_advisory_candidate" }
  | { candidate_lineage: ExamAuthoringCandidateLineage | null; gap_answers: { accepted_values: string[]; gap_id: string }[]; interaction_id: string; kind: "manual_gap_open_cloze_answer_key"; submission_origin: "teacher_authored" | "teacher_edited_advisory_candidate" | "accepted_advisory_candidate" }
  | { candidate_lineage: ExamAuthoringCandidateLineage; kind: "candidate_suppression"; suppression_reason: "teacher_rejected_candidate" }
);
export type ExamAuthoringCorrectionsApplyResult = {
  answer_key_review_state: DigiExamAnswerKeyReviewState;
  artifact_availability: { artifact_key: DigiExamMigrationTarget; availability: "available" | "unavailable"; unavailable_code?: string | null }[];
  correction_report: { accepted_entries: { applied_fields: string[]; effective_provenance?: string | null; entry_id: string; item_id: string; kind: string; sequence: number }[]; rejected_entries: Record<string, unknown>[]; schema_version: "exam_authoring_correction_report_v1" };
  effective_state: { effective_state_sha256: string; items: ExamAuthoringCorrectionSourceItem[]; schema_version: "exam_authoring_effective_state_v1" };
  request_id: string;
  schema_version: "exam_authoring_corrections_apply_result_v1";
  source_binding: ExamAuthoringCorrectionSourceStateIssueResult["source_binding"];
  target_readiness: { schema_version: typeof TARGET_READINESS_REPORT_SCHEMA_VERSION; targets: { artifact_key?: string | null; export_enabled: boolean; item_id?: string | null; message_key: string; readiness: "ready" | "target_validation_failed" | "unsupported_target_shape"; reason_code: string; sequence?: number | null; target: DigiExamMigrationTarget }[] };
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export async function sha256HexFromText(value: string): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(value));
  return Array.from(new Uint8Array(digest)).map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

function readBlobAsArrayBuffer(blob: Blob): Promise<ArrayBuffer> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      if (reader.result instanceof ArrayBuffer) {
        resolve(reader.result);
        return;
      }
      reject(new Error("Could not read upload bytes."));
    };
    reader.onerror = () => reject(reader.error ?? new Error("Could not read upload bytes."));
    reader.readAsArrayBuffer(blob);
  });
}

export async function sha256HexFromBlob(blob: Blob): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", await readBlobAsArrayBuffer(blob));
  return Array.from(new Uint8Array(digest)).map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

export function stableJsonStringify(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(stableJsonStringify).join(",")}]`;
  if (!isRecord(value)) return JSON.stringify(value);
  const entries = Object.entries(value).sort(([left], [right]) => left.localeCompare(right));
  return `{${entries
    .map(([key, item]) => `${JSON.stringify(key)}:${stableJsonStringify(item)}`)
    .join(",")}}`;
}

function readRecord(value: unknown, fieldName: string): Record<string, unknown> {
  if (isRecord(value)) return value;
  throw new Error(`Exam Converter field '${fieldName}' is not an object.`);
}

function readString(value: unknown, fieldName: string): string {
  if (typeof value === "string" && value.length > 0) return value;
  throw new Error(`Exam Converter field '${fieldName}' is missing.`);
}

function readBoolean(value: unknown, fieldName: string): boolean {
  if (typeof value === "boolean") return value;
  throw new Error(`Exam Converter field '${fieldName}' is not a boolean.`);
}

function readNullableString(value: unknown, fieldName: string): string | null {
  if (value === null || value === undefined) return null;
  return readString(value, fieldName);
}

function readNullableNumber(value: unknown, fieldName: string): number | null {
  if (value === null || value === undefined) return null;
  if (typeof value === "number" && Number.isFinite(value)) return value;
  throw new Error(`Exam Converter field '${fieldName}' is not a number.`);
}

function readReadiness(value: unknown): DigiExamTargetReadiness {
  switch (value) {
    case "ready": case "needs_teacher_answer_key": case "unsupported_target_shape":
    case "target_validation_failed": case "provider_unavailable": case "not_requested": case "not_implemented":
      return value;
    default:
      throw new Error("Exam Converter target readiness is invalid.");
  }
}

export function parseTargetReadinessReport(payload: unknown): DigiExamTargetReadinessReport {
  const root = readRecord(payload, DIGIEXAM_ARTIFACT_TARGET_READINESS_REPORT);
  if (root.schema_version !== TARGET_READINESS_REPORT_SCHEMA_VERSION || !Array.isArray(root.targets)) {
    throw new Error("Exam Converter target readiness report has an unknown schema.");
  }
  return {
    effective_exam_sha256: readString(root.effective_exam_sha256, "effective_exam_sha256"),
    job_id: readString(root.job_id, "job_id"),
    schema_version: TARGET_READINESS_REPORT_SCHEMA_VERSION,
    source_ir_sha256: readString(root.source_ir_sha256, "source_ir_sha256"),
    targets: root.targets.map((value, index) => {
      const row = readRecord(value, `targets[${index}]`);
      return {
        artifact_key: readNullableString(row.artifact_key, "artifact_key"),
        export_enabled: readBoolean(row.export_enabled, "export_enabled"),
        item_id: readNullableString(row.item_id, "item_id"),
        message_key: readString(row.message_key, "message_key"),
        readiness: readReadiness(row.readiness),
        reason_code: readString(row.reason_code, "reason_code"),
        retryable: readBoolean(row.retryable, "retryable"),
        sequence: readNullableNumber(row.sequence, "sequence"),
        source_item_fingerprint: readNullableString(row.source_item_fingerprint, "source_item_fingerprint"),
        target: readString(row.target, "target"),
        teacher_action: readString(row.teacher_action, "teacher_action"),
      };
    }),
  };
}
