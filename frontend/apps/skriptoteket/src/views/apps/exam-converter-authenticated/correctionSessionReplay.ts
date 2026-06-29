/**
 * Exam Converter correction-session replay orchestration.
 *
 * Domain purpose:
 *   Turn Skriptoteket persisted correction intents into fresh Sir Convert
 *   effective-state projection evidence without making browser drafts truth.
 *
 * Relationships:
 *   - Loads persisted current-set truth through `examConverterCorrectionSessions`.
 *   - Uses the HuleEdu Sir Convert browser Gateway client for source-state and
 *     stateless apply transport.
 *   - Feeds PR-0336 UI readback without coupling to Vue component state.
 */

import {
  getExamConverterCorrectionSession,
  type ExamConverterCorrectionIntentResponse,
  type ExamConverterCorrectionSessionResponse,
  type ExamConverterCorrectionSourceBinding,
} from "../../../api/examConverterCorrectionSessions";
import {
  applyExamAuthoringCorrections,
  issueExamAuthoringCorrectionSourceState,
  type ExamAuthoringCorrectionSourceStateIssueRequest,
  type ExamAuthoringCorrectionSourceStateIssueResult,
  type ExamAuthoringCorrectionsApplyRequest,
  type ExamAuthoringCorrectionsApplyResult,
  type ExamAuthoringNonMatchingCorrectionEntry,
} from "../../../api/sirConvertGateway";

type ReplayTarget = ExamAuthoringCorrectionsApplyRequest["requested_targets"][number];
type ReplayIntentKind = ExamConverterCorrectionIntentResponse["kind"];
type JsonRecord = Record<string, unknown>;

export type CorrectionSessionReplayDependencies = {
  applyCorrections: (params: {
    correlationId: string;
    request: ExamAuthoringCorrectionsApplyRequest;
  }) => Promise<ExamAuthoringCorrectionsApplyResult>;
  issueSourceState: (params: {
    correlationId: string;
    request: ExamAuthoringCorrectionSourceStateIssueRequest;
  }) => Promise<ExamAuthoringCorrectionSourceStateIssueResult>;
  loadCorrectionSession: (params: {
    conversionHubJobId: string;
  }) => Promise<ExamConverterCorrectionSessionResponse>;
};

export type CorrectionSessionReplayFreshResult = {
  artifactAvailability: ExamAuthoringCorrectionsApplyResult["artifact_availability"];
  answerKeyReviewState: ExamAuthoringCorrectionsApplyResult["answer_key_review_state"];
  correctionReport: ExamAuthoringCorrectionsApplyResult["correction_report"];
  correctionSession: ExamConverterCorrectionSessionResponse;
  effectiveState: ExamAuthoringCorrectionsApplyResult["effective_state"];
  projectionFreshness: "fresh";
  replayedRequestId: string;
  savedIntentCount: number;
  sourceBinding: ExamAuthoringCorrectionsApplyResult["source_binding"];
  submittedCorrectionCount: number;
  targetReadiness: ExamAuthoringCorrectionsApplyResult["target_readiness"];
};

export type CorrectionSessionReplayUnavailableResult = {
  correctionSession: ExamConverterCorrectionSessionResponse;
  projectionFreshness: "unavailable";
  reasonCode: "apply_unavailable" | "source_state_unavailable";
  savedIntentCount: number;
};

export type CorrectionSessionReplayStaleSourceResult = {
  correctionSession: ExamConverterCorrectionSessionResponse;
  projectionFreshness: "stale_source";
  reasonCode: "missing_source_binding" | "source_binding_mismatch" | "source_item_mismatch";
  savedIntentCount: number;
  staleIntentEntryIds: string[];
};

export type CorrectionSessionReplayResult =
  | CorrectionSessionReplayFreshResult
  | CorrectionSessionReplayUnavailableResult
  | CorrectionSessionReplayStaleSourceResult;

const DEFAULT_REPLAY_TARGETS: ReplayTarget[] = ["examnet_pdf", "qti_package"];
const KIND_REPLAY_ORDER: Record<ReplayIntentKind, number> = {
  candidate_suppression: 0,
  item_text_patch: 1,
  point_correction: 2,
  manual_choice_answer_key: 3,
  manual_gap_open_cloze_answer_key: 4,
};

const defaultDependencies: CorrectionSessionReplayDependencies = {
  applyCorrections: applyExamAuthoringCorrections,
  issueSourceState: issueExamAuthoringCorrectionSourceState,
  loadCorrectionSession: getExamConverterCorrectionSession,
};

export async function replayPersistedCorrectionSession(params: {
  conversionHubJobId: string;
  correlationId: string;
  dependencies?: Partial<CorrectionSessionReplayDependencies>;
  requestedTargets?: ReplayTarget[];
  sirConvertJobId: string;
}): Promise<CorrectionSessionReplayResult> {
  const dependencies = { ...defaultDependencies, ...params.dependencies };
  const correctionSession = await dependencies.loadCorrectionSession({
    conversionHubJobId: params.conversionHubJobId,
  });
  const savedIntentCount = correctionSession.active_intents.length;
  if (savedIntentCount === 0) {
    return emptyFreshReplayResult({ correctionSession });
  }

  let sourceState: ExamAuthoringCorrectionSourceStateIssueResult;
  try {
    sourceState = await dependencies.issueSourceState({
      correlationId: params.correlationId,
      request: {
        expected_source_state_sha256: correctionSession.source_binding?.source_state_sha256 ?? null,
        job_id: params.sirConvertJobId,
        schema_version: "exam_authoring_correction_source_state_issue_request_v1",
      },
    });
  } catch {
    return unavailableReplayResult({
      correctionSession,
      reasonCode: "source_state_unavailable",
    });
  }

  const staleSource = staleSourceResult({ correctionSession, sourceState });
  if (staleSource) return staleSource;

  const replayIntents = sortedReplayIntents(correctionSession.active_intents);
  const corrections = replayIntents.map(correctionEntryFromIntent);
  if (corrections.length === 0) {
    return emptyFreshReplayResult({ correctionSession });
  }
  const request: ExamAuthoringCorrectionsApplyRequest = {
    corrections,
    request_id: replayRequestId(correctionSession),
    requested_targets: params.requestedTargets ?? DEFAULT_REPLAY_TARGETS,
    schema_version: "exam_authoring_corrections_apply_request_v1",
    source_authoring_state: sourceState.source_authoring_state,
    source_binding: sourceState.source_binding,
  };

  let replay: ExamAuthoringCorrectionsApplyResult;
  try {
    replay = await dependencies.applyCorrections({
      correlationId: params.correlationId,
      request,
    });
  } catch {
    return unavailableReplayResult({
      correctionSession,
      reasonCode: "apply_unavailable",
    });
  }

  return {
    artifactAvailability: replay.artifact_availability,
    answerKeyReviewState: replay.answer_key_review_state,
    correctionReport: replay.correction_report,
    correctionSession,
    effectiveState: replay.effective_state,
    projectionFreshness: "fresh",
    replayedRequestId: replay.request_id,
    savedIntentCount,
    sourceBinding: replay.source_binding,
    submittedCorrectionCount: corrections.length,
    targetReadiness: replay.target_readiness,
  };
}

function emptyFreshReplayResult(params: {
  correctionSession: ExamConverterCorrectionSessionResponse;
}): CorrectionSessionReplayFreshResult {
  return {
    artifactAvailability: [],
    answerKeyReviewState: {
      items: [],
      schema_version: "digiexam_answer_key_review_state_v1",
    },
    correctionReport: {
      accepted_entries: [],
      rejected_entries: [],
      schema_version: "exam_authoring_correction_report_v1",
    },
    correctionSession: params.correctionSession,
    effectiveState: {
      effective_state_sha256: "",
      items: [],
      schema_version: "exam_authoring_effective_state_v1",
    },
    projectionFreshness: "fresh",
    replayedRequestId: replayRequestId(params.correctionSession),
    savedIntentCount: 0,
    sourceBinding: {
      source_authoring_schema_version: "exam_authoring_ir_v1",
      source_bundle_id: null,
      source_file_sha256: null,
      source_state_sha256: "",
      source_state_signature: "",
    },
    submittedCorrectionCount: 0,
    targetReadiness: {
      schema_version: "target_readiness_report_v1",
      targets: [],
    },
  };
}

function unavailableReplayResult(params: {
  correctionSession: ExamConverterCorrectionSessionResponse;
  reasonCode: CorrectionSessionReplayUnavailableResult["reasonCode"];
}): CorrectionSessionReplayUnavailableResult {
  return {
    correctionSession: params.correctionSession,
    projectionFreshness: "unavailable",
    reasonCode: params.reasonCode,
    savedIntentCount: params.correctionSession.active_intents.length,
  };
}

function replayRequestId(session: ExamConverterCorrectionSessionResponse): string {
  return `correction-session-replay-${session.session_id ?? session.conversion_hub_job_id}-v${session.session_version}`;
}

function sourceBindingMatches(params: {
  issued: ExamAuthoringCorrectionSourceStateIssueResult["source_binding"];
  persisted: ExamConverterCorrectionSourceBinding | null;
}): boolean {
  if (!params.persisted) return false;
  return (
    params.persisted.source_authoring_schema_version ===
      params.issued.source_authoring_schema_version &&
    nullishString(params.persisted.source_bundle_id) === nullishString(params.issued.source_bundle_id) &&
    nullishString(params.persisted.source_file_sha256) ===
      nullishString(params.issued.source_file_sha256) &&
    params.persisted.source_state_sha256 === params.issued.source_state_sha256 &&
    params.persisted.source_state_signature === params.issued.source_state_signature
  );
}

function staleSourceResult(params: {
  correctionSession: ExamConverterCorrectionSessionResponse;
  sourceState: ExamAuthoringCorrectionSourceStateIssueResult;
}): CorrectionSessionReplayStaleSourceResult | null {
  const { correctionSession, sourceState } = params;
  if (!correctionSession.source_binding) {
    return {
      correctionSession,
      projectionFreshness: "stale_source",
      reasonCode: "missing_source_binding",
      savedIntentCount: correctionSession.active_intents.length,
      staleIntentEntryIds: correctionSession.active_intents.map((intent) => intent.entry_id),
    };
  }
  if (
    !sourceBindingMatches({
      issued: sourceState.source_binding,
      persisted: correctionSession.source_binding,
    }) ||
    sourceState.source_authoring_state.source_state_sha256 !==
      correctionSession.source_binding.source_state_sha256
  ) {
    return {
      correctionSession,
      projectionFreshness: "stale_source",
      reasonCode: "source_binding_mismatch",
      savedIntentCount: correctionSession.active_intents.length,
      staleIntentEntryIds: correctionSession.active_intents.map((intent) => intent.entry_id),
    };
  }

  const sourceItemsById = new Map(
    sourceState.source_authoring_state.items.map((item) => [item.item_id, item]),
  );
  const staleIntentEntryIds = correctionSession.active_intents
    .filter((intent) => {
      const sourceItem = sourceItemsById.get(intent.item_id);
      return (
        !sourceItem ||
        sourceItem.sequence !== intent.sequence ||
        sourceItem.item_type !== intent.item_type ||
        sourceItem.source_item_fingerprint !== intent.source_item_fingerprint
      );
    })
    .map((intent) => intent.entry_id);
  if (staleIntentEntryIds.length === 0) return null;
  return {
    correctionSession,
    projectionFreshness: "stale_source",
    reasonCode: "source_item_mismatch",
    savedIntentCount: correctionSession.active_intents.length,
    staleIntentEntryIds,
  };
}

function sortedReplayIntents(
  intents: ExamConverterCorrectionIntentResponse[],
): ExamConverterCorrectionIntentResponse[] {
  return [...intents].sort(
    (left, right) =>
      left.sequence - right.sequence ||
      left.item_id.localeCompare(right.item_id) ||
      KIND_REPLAY_ORDER[left.kind] - KIND_REPLAY_ORDER[right.kind] ||
      left.target_key.localeCompare(right.target_key) ||
      left.entry_id.localeCompare(right.entry_id),
  );
}

function correctionEntryFromIntent(
  intent: ExamConverterCorrectionIntentResponse,
): ExamAuthoringNonMatchingCorrectionEntry {
  const payload = payloadRecord(intent);
  const baseEntry = {
    entry_id: intent.entry_id,
    item_id: intent.item_id,
    item_type: intent.item_type,
    sequence: intent.sequence,
    source_item_fingerprint: intent.source_item_fingerprint,
  };

  if (intent.kind === "candidate_suppression") {
    return {
      ...baseEntry,
      candidate_lineage: requiredPayloadRecord(payload, "candidate_lineage"),
      kind: "candidate_suppression",
      suppression_reason: "teacher_rejected_candidate",
    } as Extract<ExamAuthoringNonMatchingCorrectionEntry, { kind: "candidate_suppression" }>;
  }
  if (intent.kind === "item_text_patch") {
    return {
      ...baseEntry,
      kind: "item_text_patch",
      patches: requiredPayloadRecordArray(payload, "patches"),
    } as Extract<ExamAuthoringNonMatchingCorrectionEntry, { kind: "item_text_patch" }>;
  }
  if (intent.kind === "point_correction") {
    return {
      ...baseEntry,
      kind: "point_correction",
      max_score: requiredPayloadNumber(payload, "max_score"),
    } as Extract<ExamAuthoringNonMatchingCorrectionEntry, { kind: "point_correction" }>;
  }
  if (intent.kind === "manual_choice_answer_key") {
    return {
      ...baseEntry,
      candidate_lineage: optionalPayloadRecord(payload, "candidate_lineage"),
      correct_choice_ids: requiredPayloadStringArray(payload, "correct_choice_ids"),
      interaction_id: requiredPayloadString(payload, "interaction_id"),
      kind: "manual_choice_answer_key",
      submission_origin: requiredSubmissionOrigin(payload),
    } as Extract<ExamAuthoringNonMatchingCorrectionEntry, { kind: "manual_choice_answer_key" }>;
  }
  if (intent.kind === "manual_gap_open_cloze_answer_key") {
    return {
      ...baseEntry,
      candidate_lineage: optionalPayloadRecord(payload, "candidate_lineage"),
      gap_answers: requiredPayloadRecordArray(payload, "gap_answers"),
      interaction_id: requiredPayloadString(payload, "interaction_id"),
      kind: "manual_gap_open_cloze_answer_key",
      submission_origin: requiredSubmissionOrigin(payload),
    } as Extract<
      ExamAuthoringNonMatchingCorrectionEntry,
      { kind: "manual_gap_open_cloze_answer_key" }
    >;
  }
  throw new Error("Unsupported correction intent kind for replay.");
}

function payloadRecord(intent: ExamConverterCorrectionIntentResponse): JsonRecord {
  return intent.payload;
}

function nullishString(value: string | null | undefined): string | null {
  return value ?? null;
}

function isRecord(value: unknown): value is JsonRecord {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function requiredPayloadRecord(payload: JsonRecord, fieldName: string): JsonRecord {
  const value = payload[fieldName];
  if (isRecord(value)) return value;
  throw new Error(`Correction intent payload field '${fieldName}' is missing.`);
}

function optionalPayloadRecord(payload: JsonRecord, fieldName: string): JsonRecord | null {
  const value = payload[fieldName];
  if (value === null || value === undefined) return null;
  if (isRecord(value)) return value;
  throw new Error(`Correction intent payload field '${fieldName}' is invalid.`);
}

function requiredPayloadRecordArray(payload: JsonRecord, fieldName: string): JsonRecord[] {
  const value = payload[fieldName];
  if (Array.isArray(value) && value.every(isRecord)) return value;
  throw new Error(`Correction intent payload field '${fieldName}' is missing.`);
}

function requiredPayloadString(payload: JsonRecord, fieldName: string): string {
  const value = payload[fieldName];
  if (typeof value === "string" && value.length > 0) return value;
  throw new Error(`Correction intent payload field '${fieldName}' is missing.`);
}

function requiredPayloadNumber(payload: JsonRecord, fieldName: string): number {
  const value = payload[fieldName];
  if (typeof value === "number" && Number.isFinite(value)) return value;
  throw new Error(`Correction intent payload field '${fieldName}' is missing.`);
}

function requiredPayloadStringArray(payload: JsonRecord, fieldName: string): string[] {
  const value = payload[fieldName];
  if (Array.isArray(value) && value.every((entry) => typeof entry === "string")) return value;
  throw new Error(`Correction intent payload field '${fieldName}' is missing.`);
}

function requiredSubmissionOrigin(
  payload: JsonRecord,
): Extract<
  ExamAuthoringNonMatchingCorrectionEntry,
  { kind: "manual_choice_answer_key" }
>["submission_origin"] {
  const value = requiredPayloadString(payload, "submission_origin");
  if (
    value === "teacher_authored" ||
    value === "accepted_advisory_candidate" ||
    value === "teacher_edited_advisory_candidate"
  ) {
    return value;
  }
  throw new Error("Correction intent payload field 'submission_origin' is invalid.");
}
