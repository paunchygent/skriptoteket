/**
 * Exam Converter answer-key review-state adapter.
 *
 * Domain purpose:
 *   Consume Sir Convert's compact answer-key review-state projection and map
 *   producer semantics into Skriptoteket's teacher-facing review rows.
 *
 * Relationships:
 *   - Parses the first-pass `answer_key_review_state_report` artifact.
 *   - Parses correction-apply `answer_key_review_state` replay results.
 *   - Feeds question list, detail, files, and report projections without
 *     deriving review truth from IR, readiness, or local correction sessions.
 */

import type {
  DigiExamAnswerKeyReviewState,
  DigiExamAnswerKeyReviewStateItem,
} from "../../../api/sirConvertGateway";
import {
  DIGIEXAM_ANSWER_KEY_ORIGINS,
  DIGIEXAM_ANSWER_KEY_REVIEW_REASONS,
  DIGIEXAM_ANSWER_KEY_REVIEW_STATES,
  DIGIEXAM_ITEM_TYPE_MULTIPLE_RESPONSE,
  DIGIEXAM_ITEM_TYPE_OPEN_ENDED,
} from "../../../api/sirConvertGateway/contractValues";
import { ANSWER_KEY_REVIEW_STATE_SCHEMA_VERSION } from "../../../api/sirConvertGateway/schemaVersions";
import type {
  ExamConverterMissingFieldLabel,
  ExamConverterQuestionReviewRow,
  ExamConverterQuestionStatusSymbol,
} from "./digiexamIrQuestionReviewProjection";

type JsonRecord = Record<string, unknown>;

type ReviewState = DigiExamAnswerKeyReviewStateItem["review_state"];
type Origin = DigiExamAnswerKeyReviewStateItem["current_key_origin"];
type Reason = DigiExamAnswerKeyReviewStateItem["reasons"][number];

const ROOT_KEYS = new Set(["schema_version", "items"]);
const ITEM_KEYS = new Set([
  "choice_ids",
  "choice_interaction_ids",
  "correction_affordances",
  "current_key_origin",
  "gap_ids",
  "gap_interaction_ids",
  "item_id",
  "item_type",
  "message_key",
  "provenance_detail",
  "reasons",
  "replay_artifact_references",
  "review_state",
  "sequence",
  "source_item_fingerprint",
]);
const PROVENANCE_KEYS = new Set([
  "candidate_id",
  "candidate_payload_digest",
  "prompt_template_version",
  "provider_profile_id",
  "schema_name",
  "schema_version",
  "validation_state",
]);
const REPLAY_REFERENCE_KEYS = new Set(["artifact_key", "target"]);

function isRecord(value: unknown): value is JsonRecord {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function readRecord(value: unknown, fieldName: string): JsonRecord {
  if (isRecord(value)) return value;
  throw new Error(`Answer-key review-state field '${fieldName}' is not an object.`);
}

function assertKnownKeys(record: JsonRecord, allowedKeys: Set<string>, fieldName: string): void {
  for (const key of Object.keys(record)) {
    if (!allowedKeys.has(key)) {
      throw new Error(`Answer-key review-state field '${fieldName}' has unknown key '${key}'.`);
    }
  }
}

function readString(value: unknown, fieldName: string): string {
  if (typeof value === "string" && value.length > 0) return value;
  throw new Error(`Answer-key review-state field '${fieldName}' is missing.`);
}

function readNullableString(value: unknown, fieldName: string): string | null {
  if (value === null || value === undefined) return null;
  if (typeof value === "string") return value;
  throw new Error(`Answer-key review-state field '${fieldName}' is not a string.`);
}

function readNumber(value: unknown, fieldName: string): number {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  throw new Error(`Answer-key review-state field '${fieldName}' is not a number.`);
}

function readStringArray(value: unknown, fieldName: string): string[] {
  if (!Array.isArray(value)) {
    throw new Error(`Answer-key review-state field '${fieldName}' is not an array.`);
  }
  return value.map((entry, index) => readString(entry, `${fieldName}[${index}]`));
}

function readReviewState(value: unknown): ReviewState {
  const reviewState = readString(value, "review_state");
  if (DIGIEXAM_ANSWER_KEY_REVIEW_STATES.includes(reviewState as ReviewState)) {
    return reviewState as ReviewState;
  }
  throw new Error(`Unknown answer-key review_state '${reviewState}'.`);
}

function readOrigin(value: unknown): Origin {
  const origin = readString(value, "current_key_origin");
  if (DIGIEXAM_ANSWER_KEY_ORIGINS.includes(origin as Origin)) {
    return origin as Origin;
  }
  throw new Error(`Unknown answer-key current_key_origin '${origin}'.`);
}

function readReasons(value: unknown): Reason[] {
  return readStringArray(value, "reasons").map((reason) => {
    if (DIGIEXAM_ANSWER_KEY_REVIEW_REASONS.includes(reason as Reason)) {
      return reason as Reason;
    }
    throw new Error(`Unknown answer-key review reason '${reason}'.`);
  });
}

function parseProvenanceDetail(value: unknown): DigiExamAnswerKeyReviewStateItem["provenance_detail"] {
  if (value === null || value === undefined) return null;
  const detail = readRecord(value, "provenance_detail");
  assertKnownKeys(detail, PROVENANCE_KEYS, "provenance_detail");
  const validationState = readString(
    detail.validation_state,
    "provenance_detail.validation_state",
  );
  if (validationState !== "valid") {
    throw new Error(`Unknown answer-key provenance validation_state '${validationState}'.`);
  }
  return {
    candidate_id: readString(detail.candidate_id, "provenance_detail.candidate_id"),
    candidate_payload_digest: readString(
      detail.candidate_payload_digest,
      "provenance_detail.candidate_payload_digest",
    ),
    prompt_template_version: readString(
      detail.prompt_template_version,
      "provenance_detail.prompt_template_version",
    ),
    provider_profile_id: readString(
      detail.provider_profile_id,
      "provenance_detail.provider_profile_id",
    ),
    schema_name: readString(detail.schema_name, "provenance_detail.schema_name"),
    schema_version: readString(detail.schema_version, "provenance_detail.schema_version"),
    validation_state: validationState,
  };
}

function parseReplayReferences(
  value: unknown,
): DigiExamAnswerKeyReviewStateItem["replay_artifact_references"] {
  if (!Array.isArray(value)) {
    throw new Error("Answer-key review-state field 'replay_artifact_references' is not an array.");
  }
  return value.map((entry, index) => {
    const reference = readRecord(entry, `replay_artifact_references[${index}]`);
    assertKnownKeys(reference, REPLAY_REFERENCE_KEYS, `replay_artifact_references[${index}]`);
    const artifactKey = readString(reference.artifact_key, "replay_artifact_references.artifact_key");
    const target = readString(reference.target, "replay_artifact_references.target");
    if (
      (artifactKey === "correction_replay_examnet_pdf" && target === "examnet_pdf") ||
      (artifactKey === "correction_replay_qti_package" && target === "qti_package")
    ) {
      return { artifact_key: artifactKey, target };
    }
    throw new Error("Answer-key review-state replay artifact reference is unknown.");
  });
}

function parseReviewItem(value: unknown, index: number): DigiExamAnswerKeyReviewStateItem {
  const item = readRecord(value, `items[${index}]`);
  assertKnownKeys(item, ITEM_KEYS, `items[${index}]`);
  return {
    choice_ids: readStringArray(item.choice_ids ?? [], "choice_ids"),
    choice_interaction_ids: readStringArray(
      item.choice_interaction_ids ?? [],
      "choice_interaction_ids",
    ),
    correction_affordances: readStringArray(
      item.correction_affordances ?? [],
      "correction_affordances",
    ) as DigiExamAnswerKeyReviewStateItem["correction_affordances"],
    current_key_origin: readOrigin(item.current_key_origin),
    gap_ids: readStringArray(item.gap_ids ?? [], "gap_ids"),
    gap_interaction_ids: readStringArray(item.gap_interaction_ids ?? [], "gap_interaction_ids"),
    item_id: readString(item.item_id, "item_id"),
    item_type: readString(item.item_type, "item_type"),
    message_key: readString(item.message_key, "message_key"),
    provenance_detail: parseProvenanceDetail(item.provenance_detail),
    reasons: readReasons(item.reasons),
    replay_artifact_references: parseReplayReferences(item.replay_artifact_references ?? []),
    review_state: readReviewState(item.review_state),
    sequence: readNumber(item.sequence, "sequence"),
    source_item_fingerprint: readNullableString(
      item.source_item_fingerprint,
      "source_item_fingerprint",
    ),
  };
}

export function parseAnswerKeyReviewState(payload: unknown): DigiExamAnswerKeyReviewState {
  const root = readRecord(payload, "answer_key_review_state");
  assertKnownKeys(root, ROOT_KEYS, "answer_key_review_state");
  if (root.schema_version !== ANSWER_KEY_REVIEW_STATE_SCHEMA_VERSION) {
    throw new Error("Answer-key review-state has an unknown schema version.");
  }
  if (!Array.isArray(root.items)) {
    throw new Error("Answer-key review-state is missing items.");
  }
  return {
    items: root.items.map(parseReviewItem),
    schema_version: ANSWER_KEY_REVIEW_STATE_SCHEMA_VERSION,
  };
}

function reasonLabel(item: DigiExamAnswerKeyReviewStateItem): string | null {
  if (item.reasons.includes("no_correct_choice_selected")) {
    return item.item_type === DIGIEXAM_ITEM_TYPE_MULTIPLE_RESPONSE
      ? "Välj minst ett rätt svar"
      : "Inget rätt svar valt";
  }
  if (
    item.reasons.includes("required_gap_accepted_values_missing") ||
    item.reasons.includes("manual_answer_key_required")
  ) {
    return "Saknar facitsvar";
  }
  if (item.reasons.includes("target_validation_failed")) return "Målfilen behöver kontrolleras";
  if (item.reasons.includes("provider_unavailable")) return "Förslag saknas just nu";
  if (item.reasons.includes("correction_rejected")) return "Sparat facit kunde inte användas";
  if (item.reasons.includes("stale_source_state")) return "Provet har ändrats";
  if (item.reasons.includes("replay_artifact_unavailable")) return "Filen behöver skapas igen";
  if (item.reasons.includes("matching_source_state_unavailable")) return "Matchning behöver kontrolleras";
  if (item.reasons.includes("unsupported_target_shape")) return "Formatet behöver kontrolleras";
  if (item.reasons.includes("unsupported_item_type")) return "Frågetypen behöver kontrolleras";
  return null;
}

function symbolForItem(item: DigiExamAnswerKeyReviewStateItem): ExamConverterQuestionStatusSymbol {
  if (item.review_state === "review_complete") return "complete";
  if (item.review_state === "teacher_modified") return "teacher_modified";
  if (item.review_state === "validation_required") return "validation_required";
  return item.reasons.includes("advisory_candidate_pending") ? "ai_suggestion" : "validation_required";
}

function labelForState(reviewState: ReviewState): string {
  if (reviewState === "review_complete") return "Klart";
  if (reviewState === "teacher_modified") return "Ändrat";
  if (reviewState === "validation_required") return "Kontrollera";
  return "Granska";
}

function missingFieldsForItem(
  item: DigiExamAnswerKeyReviewStateItem,
  existingFields: ExamConverterMissingFieldLabel[],
): ExamConverterMissingFieldLabel[] {
  const fields = new Set<ExamConverterMissingFieldLabel>(
    existingFields.filter((field) => field !== "Facit"),
  );
  const needsAnswerKey =
    item.review_state === "validation_required" ||
    item.reasons.includes("manual_answer_key_required") ||
    item.reasons.includes("no_correct_choice_selected") ||
    item.reasons.includes("required_gap_accepted_values_missing");
  if (needsAnswerKey && item.item_type !== DIGIEXAM_ITEM_TYPE_OPEN_ENDED) {
    fields.add("Facit");
  }
  return [...fields];
}

export function applyAnswerKeyReviewStateToQuestions(params: {
  questions: ExamConverterQuestionReviewRow[];
  reviewState: DigiExamAnswerKeyReviewState;
}): ExamConverterQuestionReviewRow[] {
  const byItemId = new Map(params.reviewState.items.map((item) => [item.item_id, item]));
  return params.questions.map((question) => {
    const item = byItemId.get(question.itemId);
    if (!item) {
      throw new Error(`Answer-key review-state is missing item '${question.itemId}'.`);
    }
    const missingFields = missingFieldsForItem(item, question.missingFields);
    return {
      ...question,
      answerKeyReviewOrigin: item.current_key_origin,
      answerKeyReviewReasons: item.reasons,
      answerKeyReviewState: item.review_state,
      answerKeyReviewStateLabel: labelForState(item.review_state),
      answerKeyReviewStateReasonLabel: reasonLabel(item),
      currentAnswerKeyProvenance:
        item.current_key_origin === "reviewed_advisory"
          ? "reviewed_advisory"
          : question.currentAnswerKeyProvenance,
      llmCandidate: item.reasons.includes("advisory_candidate_pending")
        ? question.llmCandidate
        : null,
      missingFields,
      status:
        item.review_state === "review_required" || item.review_state === "validation_required"
          ? "attention"
          : "complete",
      statusSymbol: symbolForItem(item),
    };
  });
}

export function countActionableAnswerKeyRows(reviewState: DigiExamAnswerKeyReviewState): number {
  return reviewState.items.filter(
    (item) => item.review_state === "review_required" || item.review_state === "validation_required",
  ).length;
}
