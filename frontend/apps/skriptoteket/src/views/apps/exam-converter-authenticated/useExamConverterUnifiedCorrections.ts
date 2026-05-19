/**
 * Exam Converter unified correction orchestration.
 *
 * Domain purpose:
 *   Persist producer-issued Exam Authoring corrections for the authenticated
 *   Exam Converter, then replay them through Sir Convert for effective truth.
 *
 * Relationships:
 *   - Called by `ExamConverterAuthenticatedView` for durable teacher edits.
 *   - Uses `useExamConverterAuthenticatedRuntime` source-state methods.
 *   - Projects returned effective source-neutral state into review rows.
 */

import { ref, type Ref } from "vue";

import { isApiError } from "../../../api/client";
import {
  revertExamConverterCorrectionIntent,
  upsertExamConverterCorrectionIntent,
  type ExamConverterCorrectionIntentResponse,
  type ExamConverterCorrectionIntentWrite,
  type ExamConverterCorrectionSessionResponse,
} from "../../../api/examConverterCorrectionSessions";
import type {
  ExamAuthoringCorrectionsApplyRequest,
  ExamAuthoringCorrectionsApplyResult,
  ExamAuthoringCorrectionSourceStateIssueResult,
} from "../../../api/sirConvertGateway";
import type { ExamConverterRuntimeOutcome } from "./useExamConverterConversionState";
import {
  buildItemTextPatchRequest,
  buildManualAnswerKeyRequest,
  buildPointCorrectionRequest,
  type ExamConverterItemTextPatchCorrection,
  type ExamConverterManualAnswerKeyCorrection,
} from "./digiexamTeacherCorrectionOverlay";
import type {
  ExamConverterInspectionMode,
  ExamConverterQuestionReviewRow,
  ExamConverterReviewProjection,
} from "./digiexamIrReviewParser";
import { visibleMissingFieldsForQuestion } from "./digiexamIrReviewParser";
import {
  replayPersistedCorrectionSession,
  type CorrectionSessionReplayResult,
} from "./correctionSessionReplay";
import { projectUnifiedCorrectionResult } from "./correctionSessionProjection";
import {
  acceptedSuggestionIntents,
  candidateSuppressionIntent,
  intentFromCorrectionRequest,
  reviewDecisionIntents,
} from "./correctionSessionIntentBuilders";
import type { ExamConverterReviewedSuggestionDecision } from "./useExamConverterAiFacitReview";

type UnifiedCorrectionRuntime = {
  issueCorrectionSourceState: (params: {
    jobId: string;
  }) => Promise<Parameters<typeof buildPointCorrectionRequest>[0]["sourceState"]>;
};

export type ExamConverterUnifiedCorrectionOptions = {
  acceptedCurrentState: Ref<boolean>;
  activeInspectionMode: Ref<ExamConverterInspectionMode>;
  failConversion: () => void;
  finishConversion: (outcome: ExamConverterRuntimeOutcome) => void;
  isConversionRunning: Ref<boolean>;
  lastConversionHubJobId: Ref<string | null>;
  lastCorrelationId: Ref<string | null>;
  lastJobId: Ref<string | null>;
  resetFileActions: () => void;
  reviewedCompletionApplied: Ref<boolean>;
  reviewProjection: Ref<ExamConverterReviewProjection | null>;
  runtime: UnifiedCorrectionRuntime;
};

export type ExamConverterCorrectionProjectionFreshness =
  | "fresh"
  | "stale_source"
  | "unavailable"
  | "conflict"
  | null;

function replayApplyResult(
  replay: Extract<CorrectionSessionReplayResult, { projectionFreshness: "fresh" }>,
): ExamAuthoringCorrectionsApplyResult {
  return {
    artifact_availability: replay.artifactAvailability,
    correction_report: replay.correctionReport,
    effective_state: replay.effectiveState,
    request_id: replay.replayedRequestId,
    schema_version: "exam_authoring_corrections_apply_result_v1",
    source_binding: replay.sourceBinding,
    target_readiness: replay.targetReadiness,
  };
}

export function useExamConverterUnifiedCorrections(
  options: ExamConverterUnifiedCorrectionOptions,
) {
  const isCorrectionApplying = ref(false);
  const correctionProjectionFreshness = ref<ExamConverterCorrectionProjectionFreshness>(null);
  const currentCorrectionSession = ref<ExamConverterCorrectionSessionResponse | null>(null);
  const savedCorrectionIntentCount = ref(0);
  const sessionVersion = ref<number>(0);

  function setSession(session: ExamConverterCorrectionSessionResponse): void {
    currentCorrectionSession.value = session;
    savedCorrectionIntentCount.value = session.active_intents.length;
    sessionVersion.value = session.session_version;
  }

  function resetCorrectionSessionState(): void {
    correctionProjectionFreshness.value = null;
    currentCorrectionSession.value = null;
    savedCorrectionIntentCount.value = 0;
    sessionVersion.value = 0;
  }

  function sourceStateApplyResult(params: {
    projection: ExamConverterReviewProjection;
    sourceState: ExamAuthoringCorrectionSourceStateIssueResult;
  }): ExamAuthoringCorrectionsApplyResult {
    return {
      artifact_availability: [],
      correction_report: {
        accepted_entries: [],
        rejected_entries: [],
        schema_version: "exam_authoring_correction_report_v1",
      },
      effective_state: {
        effective_state_sha256: params.sourceState.source_authoring_state.source_state_sha256,
        items: params.sourceState.source_authoring_state.items,
        schema_version: "exam_authoring_effective_state_v1",
      },
      request_id: "correction-session-revert-to-source",
      schema_version: "exam_authoring_corrections_apply_result_v1",
      source_binding: params.sourceState.source_binding,
      target_readiness: {
        schema_version: "target_readiness_report_v1",
        targets: [],
      },
    };
  }

  async function replayAndProject(params: {
    conversionHubJobId: string;
    correlationId: string;
    jobId: string;
    projectEmptySession?: boolean;
    projection: ExamConverterReviewProjection;
    sourceState: ExamAuthoringCorrectionSourceStateIssueResult;
  }): Promise<boolean> {
    const replay = await replayPersistedCorrectionSession({
      conversionHubJobId: params.conversionHubJobId,
      correlationId: params.correlationId,
      sirConvertJobId: params.jobId,
    });
    setSession(replay.correctionSession);
    correctionProjectionFreshness.value = replay.projectionFreshness;
    if (replay.projectionFreshness !== "fresh") {
      if (replay.projectionFreshness === "unavailable") {
        const savedIntentProjection = projectUnifiedCorrectionResult({
          correctionSession: replay.correctionSession,
          projection: params.projection,
          result: sourceStateApplyResult({
            projection: params.projection,
            sourceState: params.sourceState,
          }),
          sourceState: params.sourceState,
        });
        options.reviewProjection.value = savedIntentProjection;
      }
      return false;
    }
    if (replay.submittedCorrectionCount === 0 && !params.projectEmptySession) {
      return false;
    }
    const result =
      replay.submittedCorrectionCount === 0
        ? sourceStateApplyResult({
            projection: params.projection,
            sourceState: params.sourceState,
          })
        : replayApplyResult(replay);
    const correctedProjection = projectUnifiedCorrectionResult({
      correctionSession: replay.correctionSession,
      projection: params.projection,
      result,
      sourceState: params.sourceState,
    });
    options.reviewProjection.value = correctedProjection;
    const visibleIssueCount = correctedProjection.questions.filter(
      (question) => visibleMissingFieldsForQuestion(question).length > 0,
    ).length;
    const needsReview =
      visibleIssueCount > 0 ||
      correctedProjection.files.some((file) => !file.exportEnabled);
    options.finishConversion({
      artifactCount: correctedProjection.files.length,
      bundleStatus: needsReview ? "needs_review" : "complete",
      manualFollowUpCount: visibleIssueCount,
      manualFollowUpRequired: visibleIssueCount > 0,
      warningCount: correctedProjection.report.warningCount,
    });
    options.activeInspectionMode.value = "questions";
    return true;
  }

  async function upsertIntents(params: {
    conversionHubJobId: string;
    intents: ExamConverterCorrectionIntentWrite[];
  }): Promise<void> {
    for (const intent of params.intents) {
      const session = await upsertExamConverterCorrectionIntent({
        conversionHubJobId: params.conversionHubJobId,
        request: {
          expected_session_version: sessionVersion.value,
          intent,
        },
      });
      setSession(session);
    }
  }

  async function applyPersistedIntents(params: {
    intents: ExamConverterCorrectionIntentWrite[];
    projection: ExamConverterReviewProjection;
    sourceState: ExamAuthoringCorrectionSourceStateIssueResult;
  }): Promise<boolean> {
    const jobId = options.lastJobId.value;
    const conversionHubJobId = options.lastConversionHubJobId.value;
    const correlationId = options.lastCorrelationId.value;
    if (!jobId || !conversionHubJobId || !correlationId || params.intents.length === 0) {
      return false;
    }
    await upsertIntents({ conversionHubJobId, intents: params.intents });
    return await replayAndProject({
      conversionHubJobId,
      correlationId,
      jobId,
      projection: params.projection,
      sourceState: params.sourceState,
    });
  }

  async function refreshPersistedCorrections(): Promise<void> {
    const projection = options.reviewProjection.value;
    const jobId = options.lastJobId.value;
    const conversionHubJobId = options.lastConversionHubJobId.value;
    const correlationId = options.lastCorrelationId.value;
    if (!projection || !jobId || !conversionHubJobId || !correlationId) {
      return;
    }
    try {
      const sourceState = await options.runtime.issueCorrectionSourceState({ jobId });
      await replayAndProject({ conversionHubJobId, correlationId, jobId, projection, sourceState });
    } catch (error) {
      console.error("Exam Converter correction-session readback failed.", error);
      correctionProjectionFreshness.value = "unavailable";
    }
  }

  async function applyCorrection(
    buildRequest: (params: {
      projection: ExamConverterReviewProjection;
      sourceState: Awaited<ReturnType<UnifiedCorrectionRuntime["issueCorrectionSourceState"]>>;
    }) => ExamAuthoringCorrectionsApplyRequest,
  ): Promise<void> {
    const projection = options.reviewProjection.value;
    const jobId = options.lastJobId.value;
    const conversionHubJobId = options.lastConversionHubJobId.value;
    const correlationId = options.lastCorrelationId.value;
    if (
      !projection ||
      !jobId ||
      !conversionHubJobId ||
      !correlationId ||
      options.isConversionRunning.value ||
      isCorrectionApplying.value
    ) {
      return;
    }
    options.resetFileActions();
    isCorrectionApplying.value = true;
    try {
      const sourceState = await options.runtime.issueCorrectionSourceState({ jobId });
      const request = buildRequest({ projection, sourceState });
      const projected = await applyPersistedIntents({
        intents: [intentFromCorrectionRequest(request)],
        projection,
        sourceState,
      });
      if (!projected) {
        return;
      }
      options.acceptedCurrentState.value = false;
      options.reviewedCompletionApplied.value = false;
    } catch (error) {
      console.error("Exam Converter teacher correction apply failed.", error);
      correctionProjectionFreshness.value =
        isApiError(error) && error.status === 409 ? "conflict" : "unavailable";
      options.failConversion();
    } finally {
      isCorrectionApplying.value = false;
    }
  }

  function applyPointCorrection(
    question: ExamConverterQuestionReviewRow,
    maxScore: number,
  ): Promise<void> {
    return applyCorrection(({ projection, sourceState }) =>
      buildPointCorrectionRequest({ maxScore, projection, question, sourceState }),
    );
  }

  function applyManualAnswerKey(
    question: ExamConverterQuestionReviewRow,
    answerKey: ExamConverterManualAnswerKeyCorrection,
  ): Promise<void> {
    return applyCorrection(({ projection, sourceState }) =>
      buildManualAnswerKeyRequest({ answerKey, projection, question, sourceState }),
    );
  }

  function applyItemTextPatch(
    question: ExamConverterQuestionReviewRow,
    patch: ExamConverterItemTextPatchCorrection,
  ): Promise<void> {
    return applyCorrection(({ projection, sourceState }) =>
      buildItemTextPatchRequest({ patch, projection, question, sourceState }),
    );
  }

  async function applyReviewDecision(): Promise<boolean> {
    const projection = options.reviewProjection.value;
    const jobId = options.lastJobId.value;
    if (!projection || !jobId || options.isConversionRunning.value || isCorrectionApplying.value) {
      return false;
    }
    options.resetFileActions();
    isCorrectionApplying.value = true;
    try {
      const sourceState = await options.runtime.issueCorrectionSourceState({ jobId });
      const projected = await applyPersistedIntents({
        intents: reviewDecisionIntents({ projection, sourceState }),
        projection,
        sourceState,
      });
      options.acceptedCurrentState.value = projected;
      return projected;
    } catch (error) {
      console.error("Exam Converter review decision apply failed.", error);
      correctionProjectionFreshness.value =
        isApiError(error) && error.status === 409 ? "conflict" : "unavailable";
      options.failConversion();
      return false;
    } finally {
      isCorrectionApplying.value = false;
    }
  }

  async function applyReviewedSuggestions(
    decisions: Record<string, ExamConverterReviewedSuggestionDecision>,
  ): Promise<boolean> {
    const projection = options.reviewProjection.value;
    const jobId = options.lastJobId.value;
    if (!projection || !jobId || options.isConversionRunning.value || isCorrectionApplying.value) {
      return false;
    }
    options.resetFileActions();
    isCorrectionApplying.value = true;
    try {
      const sourceState = await options.runtime.issueCorrectionSourceState({ jobId });
      const projected = await applyPersistedIntents({
        intents: acceptedSuggestionIntents({ decisions, projection, sourceState }),
        projection,
        sourceState,
      });
      options.reviewedCompletionApplied.value = projected;
      return projected;
    } catch (error) {
      console.error("Exam Converter reviewed suggestion apply failed.", error);
      correctionProjectionFreshness.value =
        isApiError(error) && error.status === 409 ? "conflict" : "unavailable";
      options.failConversion();
      return false;
    } finally {
      isCorrectionApplying.value = false;
    }
  }

  async function suppressCandidate(question: ExamConverterQuestionReviewRow): Promise<boolean> {
    const projection = options.reviewProjection.value;
    const jobId = options.lastJobId.value;
    if (!projection || !jobId || options.isConversionRunning.value || isCorrectionApplying.value) {
      return false;
    }
    options.resetFileActions();
    isCorrectionApplying.value = true;
    try {
      const sourceState = await options.runtime.issueCorrectionSourceState({ jobId });
      return await applyPersistedIntents({
        intents: [candidateSuppressionIntent({ question, sourceState })],
        projection,
        sourceState,
      });
    } catch (error) {
      console.error("Exam Converter candidate suppression failed.", error);
      correctionProjectionFreshness.value =
        isApiError(error) && error.status === 409 ? "conflict" : "unavailable";
      options.failConversion();
      return false;
    } finally {
      isCorrectionApplying.value = false;
    }
  }

  function answerKeyIntentForQuestion(
    question: ExamConverterQuestionReviewRow,
  ): ExamConverterCorrectionIntentResponse | null {
    const session = currentCorrectionSession.value;
    if (!session) return null;
    return (
      session.active_intents.find(
        (intent) =>
          intent.item_id === question.itemId &&
          (intent.kind === "manual_choice_answer_key" ||
            intent.kind === "manual_gap_open_cloze_answer_key"),
      ) ?? null
    );
  }

  async function revertAnswerKey(question: ExamConverterQuestionReviewRow): Promise<boolean> {
    const projection = options.reviewProjection.value;
    const jobId = options.lastJobId.value;
    const conversionHubJobId = options.lastConversionHubJobId.value;
    const correlationId = options.lastCorrelationId.value;
    const intent = answerKeyIntentForQuestion(question);
    if (
      !projection ||
      !jobId ||
      !conversionHubJobId ||
      !correlationId ||
      !intent ||
      options.isConversionRunning.value ||
      isCorrectionApplying.value
    ) {
      return false;
    }
    options.resetFileActions();
    isCorrectionApplying.value = true;
    try {
      const session = await revertExamConverterCorrectionIntent({
        conversionHubJobId,
        request: {
          expected_session_version: sessionVersion.value,
          target_key: intent.target_key,
        },
      });
      setSession(session);
      const sourceState = await options.runtime.issueCorrectionSourceState({ jobId });
      return await replayAndProject({
        conversionHubJobId,
        correlationId,
        jobId,
        projectEmptySession: true,
        projection,
        sourceState,
      });
    } catch (error) {
      console.error("Exam Converter answer-key revert failed.", error);
      correctionProjectionFreshness.value =
        isApiError(error) && error.status === 409 ? "conflict" : "unavailable";
      options.failConversion();
      return false;
    } finally {
      isCorrectionApplying.value = false;
    }
  }

  return {
    applyItemTextPatch,
    applyManualAnswerKey,
    applyPointCorrection,
    applyReviewDecision,
    applyReviewedSuggestions,
    correctionProjectionFreshness,
    isCorrectionApplying,
    refreshPersistedCorrections,
    revertAnswerKey,
    resetCorrectionSessionState,
    savedCorrectionIntentCount,
    suppressCandidate,
  };
}
