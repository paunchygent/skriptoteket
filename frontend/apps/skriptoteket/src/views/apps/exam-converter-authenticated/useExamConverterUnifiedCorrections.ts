/**
 * Exam Converter unified correction orchestration.
 *
 * Domain purpose:
 *   Persist producer-issued Exam Authoring corrections for the authenticated
 *   Exam Converter, then replay them through Skriptoteket-owned conversion state.
 *
 * Relationships:
 *   - Called by `ExamConverterAuthenticatedView` for durable teacher edits.
 *   - Uses `useExamConverterAuthenticatedRuntime` source-state methods.
 *   - Reloads the locally projected review and readiness artifacts after replay.
 */

import { ref, type Ref } from "vue";

import { isApiError } from "../../../api/client";
import {
  getExamConverterCorrectionSession,
  upsertExamConverterCorrectionIntent,
  type ExamConverterCorrectionIntentWrite,
  type ExamConverterCorrectionSessionResponse,
} from "../../../api/examConverterCorrectionSessions";
import { replayLocalExamConversion } from "../../../api/examConverterLocal";
import type {
  ExamAuthoringCorrectionsApplyRequest,
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
  candidateSuppressionIntent,
  intentFromCorrectionRequest,
} from "./correctionSessionIntentBuilders";

type UnifiedCorrectionRuntime = {
  issueCorrectionSourceState: (params: {
    jobId: string;
  }) => Promise<Parameters<typeof buildPointCorrectionRequest>[0]["sourceState"]>;
};

export type ExamConverterUnifiedCorrectionOptions = {
  activeInspectionMode: Ref<ExamConverterInspectionMode>;
  failConversion: () => void;
  finishConversion: (outcome: ExamConverterRuntimeOutcome) => void;
  isConversionRunning: Ref<boolean>;
  lastConversionHubJobId: Ref<string | null>;
  lastCorrelationId: Ref<string | null>;
  lastJobId: Ref<string | null>;
  loadReviewArtifacts: (params: {
    completionReportRequired?: boolean;
    correlationId: string;
    jobId: string;
  }) => Promise<ExamConverterReviewProjection | null>;
  resetFileActions: () => void;
  reviewProjection: Ref<ExamConverterReviewProjection | null>;
  runtime: UnifiedCorrectionRuntime;
};

export type ExamConverterCorrectionProjectionFreshness =
  | "fresh"
  | "stale_source"
  | "unavailable"
  | "conflict"
  | null;

export function useExamConverterUnifiedCorrections(
  options: ExamConverterUnifiedCorrectionOptions,
) {
  const isCorrectionApplying = ref(false);
  const correctionProjectionFreshness = ref<ExamConverterCorrectionProjectionFreshness>(null);
  const sessionVersion = ref<number>(0);

  function setSession(session: ExamConverterCorrectionSessionResponse): void {
    sessionVersion.value = session.session_version;
  }

  function resetCorrectionSessionState(): void {
    correctionProjectionFreshness.value = null;
    sessionVersion.value = 0;
  }

  async function replayAndProject(params: {
    conversionHubJobId: string;
    correlationId: string;
    jobId: string;
    projection: ExamConverterReviewProjection;
  }): Promise<boolean> {
    const session = await getExamConverterCorrectionSession({
      conversionHubJobId: params.conversionHubJobId,
    });
    setSession(session);
    if (session.active_intents.length === 0) {
      correctionProjectionFreshness.value = "fresh";
      return false;
    }
    await replayLocalExamConversion({
      correlationId: params.correlationId,
      jobId: params.jobId,
    });
    const correctedProjection = await options.loadReviewArtifacts({
      completionReportRequired: false,
      correlationId: params.correlationId,
      jobId: params.jobId,
    });
    correctionProjectionFreshness.value = correctedProjection ? "fresh" : "unavailable";
    if (!correctedProjection) return false;
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
      await replayAndProject({ conversionHubJobId, correlationId, jobId, projection });
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
      });
      if (!projected) {
        return;
      }
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

  return {
    applyItemTextPatch,
    applyManualAnswerKey,
    applyPointCorrection,
    correctionProjectionFreshness,
    isCorrectionApplying,
    refreshPersistedCorrections,
    resetCorrectionSessionState,
    suppressCandidate,
  };
}
