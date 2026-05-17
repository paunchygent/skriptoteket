/**
 * DigiExam answer-key completion projection.
 *
 * Domain purpose:
 *   Validate Sir Convert's advisory answer-key completion report and expose
 *   bounded AI-facit candidate data for authenticated teacher review.
 *
 * Relationships:
 *   - Consumed by `useExamConverterReviewArtifacts` beside IR and readiness
 *     artifacts.
 *   - Joined into question rows by `digiexamIrReviewParser`.
 *   - Feeds reviewed-completion overlay construction without exposing raw
 *     provider responses or prompt internals.
 */

import type {
  DigiExamAnswerKeyCompletionReportItem,
  DigiExamEffectiveAnswerKey,
  DigiExamEffectiveExam,
  DigiExamItemType,
} from "../../../api/sirConvertGateway";
import {
  DIGIEXAM_COMPLETION_MODE_SUGGEST_MISSING_MACHINE_MARKED,
  DIGIEXAM_ITEM_TYPE_GAP_FILL,
  DIGIEXAM_ITEM_TYPE_MULTIPLE_CHOICE,
  DIGIEXAM_ITEM_TYPE_MULTIPLE_RESPONSE,
  DIGIEXAM_ITEM_TYPE_SINGLE_CHOICE,
  DIGIEXAM_ITEM_TYPES,
} from "../../../api/sirConvertGateway/contractValues";
import {
  ANSWER_KEY_COMPLETION_REPORT_SCHEMA_VERSION,
  DIGIEXAM_EFFECTIVE_EXAM_SCHEMA_VERSION,
} from "../../../api/sirConvertGateway/schemaVersions";

type JsonRecord = Record<string, unknown>;

export type ExamConverterCompletionDecisionState =
  DigiExamAnswerKeyCompletionReportItem["decision_state"];
export type ExamConverterCompletionValidationState =
  DigiExamAnswerKeyCompletionReportItem["validation_state"];

export type ExamConverterChoiceAnswerPayload = {
  kind: "choice";
  correctAlternativeIds: number[];
};

export type ExamConverterGapFillAnswerPayload = {
  kind: "gap_fill";
  gapAnswers: {
    acceptedValues: string[];
    gapId: string;
  }[];
};

export type ExamConverterCompletionAnswerPayload =
  | ExamConverterChoiceAnswerPayload
  | ExamConverterGapFillAnswerPayload;

export type ExamConverterLlmAnswerKeyCandidate = {
  answerPayload: ExamConverterCompletionAnswerPayload | null;
  backendFailureCode: string | null;
  backendStatus: string;
  candidateId: string | null;
  candidatePayloadDigest: string | null;
  completionReportSha256: string;
  decisionState: ExamConverterCompletionDecisionState;
  itemId: string;
  itemType: string;
  modelProfile: string | null;
  promptTemplateVersion: string | null;
  providerProfileId: string | null;
  schemaName: string | null;
  schemaVersion: string | null;
  sequence: number;
  validationState: ExamConverterCompletionValidationState;
};

export type ExamConverterAnswerKeyCompletionReport = {
  completionReportSha256: string;
  itemsByItemId: Map<string, ExamConverterLlmAnswerKeyCandidate>;
};

export type ExamConverterEffectiveAnswerKeyByItem = Map<string, DigiExamEffectiveAnswerKey>;

const PROVIDER_REQUEST_FAILED = "provider_request_failed";
const ADVISORY_MACHINE_MARKED_ITEM_TYPES = new Set<string>([
  DIGIEXAM_ITEM_TYPE_GAP_FILL,
  DIGIEXAM_ITEM_TYPE_MULTIPLE_CHOICE,
  DIGIEXAM_ITEM_TYPE_MULTIPLE_RESPONSE,
  DIGIEXAM_ITEM_TYPE_SINGLE_CHOICE,
]);

function isRecord(value: unknown): value is JsonRecord {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function readRecord(value: unknown, fieldName: string): JsonRecord {
  if (isRecord(value)) return value;
  throw new Error(`DigiExam completion report field '${fieldName}' is not an object.`);
}

function readString(value: unknown, fieldName: string): string {
  if (typeof value === "string" && value.length > 0) return value;
  throw new Error(`DigiExam completion report field '${fieldName}' is missing.`);
}

function readNullableString(value: unknown, fieldName: string): string | null {
  if (value === null || value === undefined) return null;
  if (typeof value === "string") return value;
  throw new Error(`DigiExam completion report field '${fieldName}' is not a string.`);
}

function readNumber(value: unknown, fieldName: string): number {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  throw new Error(`DigiExam completion report field '${fieldName}' is not a number.`);
}

function readStringArray(value: unknown, fieldName: string): string[] {
  if (!Array.isArray(value)) {
    throw new Error(`DigiExam completion report field '${fieldName}' is not an array.`);
  }
  return value.map((entry, index) => readString(entry, `${fieldName}[${index}]`));
}

function readNumberArray(value: unknown, fieldName: string): number[] {
  if (!Array.isArray(value)) {
    throw new Error(`DigiExam completion report field '${fieldName}' is not an array.`);
  }
  return value.map((entry, index) => readNumber(entry, `${fieldName}[${index}]`));
}

function readRecordArray(value: unknown, fieldName: string): JsonRecord[] {
  if (!Array.isArray(value)) {
    throw new Error(`DigiExam completion report field '${fieldName}' is not an array.`);
  }
  return value.map((entry, index) => readRecord(entry, `${fieldName}[${index}]`));
}

function readDecisionState(value: unknown): ExamConverterCompletionDecisionState {
  const state = readString(value, "decision_state");
  if (state === "suggested" || state === "manual_follow_up_required" || state === "skipped") {
    return state;
  }
  throw new Error(`Unknown DigiExam completion decision state '${state}'.`);
}

function readValidationState(value: unknown): ExamConverterCompletionValidationState {
  const state = readString(value, "validation_state");
  if (state === "valid" || state === "invalid" || state === "manual_follow_up_required" || state === "skipped") {
    return state;
  }
  throw new Error(`Unknown DigiExam completion validation state '${state}'.`);
}

function parseGapAnswers(value: unknown): ExamConverterGapFillAnswerPayload["gapAnswers"] {
  return readRecordArray(value, "answer_payload.gap_answers").map((entry, index) => ({
    acceptedValues: readStringArray(
      entry.accepted_values,
      `answer_payload.gap_answers[${index}].accepted_values`,
    ),
    gapId: readString(entry.gap_id, `answer_payload.gap_answers[${index}].gap_id`),
  }));
}

function parseAnswerPayload(value: unknown): ExamConverterCompletionAnswerPayload | null {
  if (value === null || value === undefined) return null;
  const record = readRecord(value, "answer_payload");
  const kind = readString(record.kind, "answer_payload.kind");
  if (kind === "choice") {
    return {
      kind,
      correctAlternativeIds: readNumberArray(
        record.correct_alternative_ids,
        "answer_payload.correct_alternative_ids",
      ),
    };
  }
  if (kind === "gap_fill") {
    return {
      kind,
      gapAnswers: parseGapAnswers(record.gap_answers),
    };
  }
  throw new Error(`Unsupported DigiExam completion answer payload kind '${kind}'.`);
}

function isSupportedItemType(value: string): value is DigiExamItemType {
  return DIGIEXAM_ITEM_TYPES.includes(value as DigiExamItemType);
}

function assertValidCandidateLineage(candidate: ExamConverterLlmAnswerKeyCandidate): void {
  if (candidate.validationState !== "valid" || candidate.decisionState !== "suggested") {
    return;
  }
  if (
    !candidate.answerPayload ||
    !candidate.candidateId ||
    !candidate.candidatePayloadDigest ||
    !candidate.providerProfileId ||
    !candidate.promptTemplateVersion ||
    !candidate.schemaName ||
    !candidate.schemaVersion
  ) {
    throw new Error("Valid DigiExam completion candidates require bounded lineage.");
  }
}

function parseReportItem(
  value: unknown,
  completionReportSha256: string,
): ExamConverterLlmAnswerKeyCandidate {
  const record = readRecord(value, "items[]");
  const itemType = readString(record.item_type, "item_type");
  if (!isSupportedItemType(itemType)) {
    throw new Error(`Unknown DigiExam completion item type '${itemType}'.`);
  }
  const candidate = {
    answerPayload: parseAnswerPayload(record.answer_payload),
    backendFailureCode: readNullableString(record.backend_failure_code, "backend_failure_code"),
    backendStatus: readString(record.backend_status, "backend_status"),
    candidateId: readNullableString(record.candidate_id, "candidate_id"),
    candidatePayloadDigest: readNullableString(
      record.candidate_payload_digest,
      "candidate_payload_digest",
    ),
    completionReportSha256,
    decisionState: readDecisionState(record.decision_state),
    itemId: readString(record.item_id, "item_id"),
    itemType,
    modelProfile: readNullableString(record.model_profile, "model_profile"),
    promptTemplateVersion: readNullableString(
      record.prompt_template_version,
      "prompt_template_version",
    ),
    providerProfileId: readNullableString(record.provider_profile_id, "provider_profile_id"),
    schemaName: readNullableString(record.schema_name, "schema_name"),
    schemaVersion: readNullableString(record.schema_version, "schema_version"),
    sequence: readNumber(record.sequence, "sequence"),
    validationState: readValidationState(record.validation_state),
  };
  assertValidCandidateLineage(candidate);
  return candidate;
}

export function parseAnswerKeyCompletionReport(params: {
  payload: unknown;
  completionReportSha256: string;
}): ExamConverterAnswerKeyCompletionReport {
  const root = readRecord(params.payload, "answer_key_completion_report");
  if (root.schema_version !== ANSWER_KEY_COMPLETION_REPORT_SCHEMA_VERSION) {
    throw new Error("DigiExam completion report has an unsupported schema version.");
  }
  if (root.completion_mode !== DIGIEXAM_COMPLETION_MODE_SUGGEST_MISSING_MACHINE_MARKED) {
    throw new Error("DigiExam completion report has an unsupported completion mode.");
  }
  const itemsByItemId = new Map<string, ExamConverterLlmAnswerKeyCandidate>();
  for (const item of readRecordArray(root.items, "items")) {
    const candidate = parseReportItem(item, params.completionReportSha256);
    itemsByItemId.set(candidate.itemId, candidate);
  }
  return {
    completionReportSha256: params.completionReportSha256,
    itemsByItemId,
  };
}

function isMachineMarkedAdvisoryCandidate(candidate: ExamConverterLlmAnswerKeyCandidate): boolean {
  return ADVISORY_MACHINE_MARKED_ITEM_TYPES.has(candidate.itemType);
}

function isValidAnswerPayload(candidate: ExamConverterLlmAnswerKeyCandidate): boolean {
  return (
    candidate.answerPayload !== null &&
    candidate.decisionState === "suggested" &&
    candidate.validationState === "valid"
  );
}

export function isProviderOnlyAdvisoryFailureReport(
  report: ExamConverterAnswerKeyCompletionReport | null,
): boolean {
  if (!report) return false;
  const candidates = Array.from(report.itemsByItemId.values());
  const eligibleCandidates = candidates.filter(isMachineMarkedAdvisoryCandidate);
  return (
    eligibleCandidates.length > 0 &&
    candidates.every((candidate) => !isValidAnswerPayload(candidate)) &&
    eligibleCandidates.every(
      (candidate) => candidate.backendFailureCode === PROVIDER_REQUEST_FAILED,
    )
  );
}

export function parseEffectiveAnswerKeysByItem(payload: unknown): ExamConverterEffectiveAnswerKeyByItem {
  const root = readRecord(payload, "effective_ir_json") as DigiExamEffectiveExam;
  if (root.schema_version !== DIGIEXAM_EFFECTIVE_EXAM_SCHEMA_VERSION) {
    throw new Error("DigiExam effective IR artifact has an unsupported schema version.");
  }
  const itemsByItemId = new Map<string, DigiExamEffectiveAnswerKey>();
  for (const item of root.items) {
    if (item.effective_answer_key) {
      itemsByItemId.set(item.item_id, item.effective_answer_key);
    }
  }
  return itemsByItemId;
}
