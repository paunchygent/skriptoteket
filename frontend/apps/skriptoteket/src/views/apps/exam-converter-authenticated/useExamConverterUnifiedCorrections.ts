/**
 * Exam Converter unified correction orchestration.
 *
 * Domain purpose:
 *   Apply producer-issued Exam Authoring corrections for the authenticated
 *   Exam Converter without mutating source IR or browser-local file readiness.
 *
 * Relationships:
 *   - Called by `ExamConverterAuthenticatedView` for PR-0332 teacher edits.
 *   - Uses `useExamConverterAuthenticatedRuntime` source-state/apply methods.
 *   - Projects returned effective source-neutral state into review rows.
 */

import { ref, type Ref } from "vue";

import type {
  ExamAuthoringCorrectionsApplyRequest,
  ExamAuthoringCorrectionsApplyResult,
  ExamAuthoringCorrectionSourceItem,
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
import { hasUsableCompletionCandidate } from "./digiexamIrReviewParser";

type UnifiedCorrectionRuntime = {
  applyCorrectionRequest: (
    request: ExamAuthoringCorrectionsApplyRequest,
  ) => Promise<ExamAuthoringCorrectionsApplyResult>;
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
  lastJobId: Ref<string | null>;
  resetFileActions: () => void;
  reviewedCompletionApplied: Ref<boolean>;
  reviewProjection: Ref<ExamConverterReviewProjection | null>;
  runtime: UnifiedCorrectionRuntime;
};

function stripHtml(value: string): string {
  return value.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();
}

function promptTextForSourceItem(item: ExamAuthoringCorrectionSourceItem): string {
  const joinedLines = item.prompt_lines.join(" ").trim();
  if (joinedLines.length > 0) return joinedLines;
  if (item.prompt_html) return stripHtml(item.prompt_html);
  return item.title ?? "";
}

function sourceChoicesForAnswerKey(params: {
  effectiveItem: ExamAuthoringCorrectionSourceItem;
  sourceItem: ExamAuthoringCorrectionSourceItem | null;
}) {
  const effectiveChoices = params.effectiveItem.choice_interactions[0]?.choices ?? [];
  if (effectiveChoices.length > 0) return effectiveChoices;
  return params.sourceItem?.choice_interactions[0]?.choices ?? [];
}

function displayIdForSourceChoice(
  choice: ReturnType<typeof sourceChoicesForAnswerKey>[number] | undefined,
): number | null {
  if (!choice) return null;
  const sourceId = Number.parseInt(choice.source_id ?? "", 10);
  if (Number.isInteger(sourceId)) return sourceId;
  return Number.isInteger(choice.order) ? choice.order : null;
}

function isIntegerChoiceId(value: number | null): value is number {
  return Number.isInteger(value);
}

function effectiveAnswerKeyForSourceItem(params: {
  effectiveItem: ExamAuthoringCorrectionSourceItem;
  sourceItem: ExamAuthoringCorrectionSourceItem | null;
}) {
  const { effectiveItem } = params;
  const choiceAnswerKey = effectiveItem.choice_interactions[0]?.answer_key;
  if (choiceAnswerKey?.provenance && choiceAnswerKey.provenance !== "absent") {
    const choices = sourceChoicesForAnswerKey(params);
    return {
      correct_alternative_ids: choiceAnswerKey.correct_choice_ids
        .map((choiceId) => choices.find((choice) => choice.choice_id === choiceId))
        .map(displayIdForSourceChoice)
        .filter(isIntegerChoiceId),
      lineage: null,
      provenance: choiceAnswerKey.provenance,
    };
  }
  const gapAnswerKey = effectiveItem.gap_open_cloze_interactions[0]?.answer_key;
  if (gapAnswerKey?.provenance && gapAnswerKey.provenance !== "absent") {
    return {
      correct_gap_answers: gapAnswerKey.accepted_values.map((acceptedValue) => ({
        [acceptedValue.gap_id]: acceptedValue.value,
      })),
      lineage: null,
      provenance: gapAnswerKey.provenance,
    };
  }
  return null;
}

function reportForCorrectedQuestions(
  projection: ExamConverterReviewProjection,
  questions: ExamConverterQuestionReviewRow[],
) {
  return {
    ...projection.report,
    aiSuggestionCount: questions.filter(hasUsableCompletionCandidate).length,
    attentionQuestionCount: questions.filter((question) => question.missingFields.length > 0)
      .length,
    missingAnswerKeyCount: questions.filter((question) =>
      question.missingFields.includes("Facit"),
    ).length,
    missingPointsCount: questions.filter((question) =>
      question.missingFields.includes("Poäng"),
    ).length,
  };
}

function projectUnifiedCorrectionResult(params: {
  projection: ExamConverterReviewProjection;
  result: ExamAuthoringCorrectionsApplyResult;
  sourceState: ExamAuthoringCorrectionSourceStateIssueResult;
}): ExamConverterReviewProjection {
  const effectiveItemsById = new Map(
    params.result.effective_state.items.map((item) => [item.item_id, item]),
  );
  const sourceItemsById = new Map(
    params.sourceState.source_authoring_state.items.map((item) => [item.item_id, item]),
  );
  const questions = params.projection.questions.map((question): ExamConverterQuestionReviewRow => {
    const effectiveItem = effectiveItemsById.get(question.itemId);
    if (!effectiveItem) return question;
    const sourceItem = sourceItemsById.get(question.itemId) ?? null;
    const effectiveMaxScore =
      typeof effectiveItem.max_score === "number" ? effectiveItem.max_score : null;
    const effectivePointCorrection =
      effectiveMaxScore === question.pointsValue || effectiveMaxScore === null
        ? question.effectivePointCorrection
        : {
            effective_max_score: effectiveMaxScore,
            kind: "item_points" as const,
            source_item_fingerprint: question.sourceItemFingerprint ?? "",
            source_max_score: question.pointsValue,
          };
    const effectiveAnswerKey = effectiveAnswerKeyForSourceItem({ effectiveItem, sourceItem });
    const pointsValue = effectiveMaxScore ?? question.pointsValue;
    const missingFields = question.missingFields.filter((field) => {
      if (field === "Poäng") return effectivePointCorrection === null;
      if (field === "Facit") return effectiveAnswerKey === null;
      return true;
    });
    const llmCandidate = effectiveAnswerKey ? null : question.llmCandidate;
    return {
      ...question,
      currentAnswerKeyProvenance:
        effectiveAnswerKey?.provenance ?? question.currentAnswerKeyProvenance,
      effectiveAnswerKey: effectiveAnswerKey ?? question.effectiveAnswerKey,
      effectivePointCorrection,
      llmCandidate,
      missingFields,
      pointsLabel: pointsValue === null ? "—" : `${pointsValue.toLocaleString("sv-SE")} p`,
      pointsValue,
      promptText: promptTextForSourceItem(effectiveItem) || question.promptText,
      status: missingFields.length > 0 ? question.status : "complete",
      statusSymbol: hasUsableCompletionCandidate({ llmCandidate })
        ? "ai_suggestion"
        : missingFields.includes("Facit") && question.itemType !== "open_ended"
          ? "missing"
          : "complete",
      title: effectiveItem.title ?? question.title,
    };
  });
  return {
    ...params.projection,
    questions,
    report: reportForCorrectedQuestions(params.projection, questions),
  };
}

export function useExamConverterUnifiedCorrections(
  options: ExamConverterUnifiedCorrectionOptions,
) {
  const isCorrectionApplying = ref(false);

  async function applyCorrection(
    buildRequest: (params: {
      projection: ExamConverterReviewProjection;
      sourceState: Awaited<ReturnType<UnifiedCorrectionRuntime["issueCorrectionSourceState"]>>;
    }) => ExamAuthoringCorrectionsApplyRequest,
  ): Promise<void> {
    const projection = options.reviewProjection.value;
    const jobId = options.lastJobId.value;
    if (!projection || !jobId || options.isConversionRunning.value || isCorrectionApplying.value) {
      return;
    }
    options.resetFileActions();
    isCorrectionApplying.value = true;
    try {
      const sourceState = await options.runtime.issueCorrectionSourceState({ jobId });
      const request = buildRequest({ projection, sourceState });
      const result = await options.runtime.applyCorrectionRequest(request);
      options.acceptedCurrentState.value = false;
      options.reviewedCompletionApplied.value = false;
      const correctedProjection = projectUnifiedCorrectionResult({
        projection,
        result,
        sourceState,
      });
      options.reviewProjection.value = correctedProjection;
      options.finishConversion({
        artifactCount: correctedProjection.files.length,
        bundleStatus: "needs_review",
        manualFollowUpCount: correctedProjection.report.attentionQuestionCount,
        manualFollowUpRequired: correctedProjection.report.attentionQuestionCount > 0,
        warningCount: correctedProjection.report.warningCount,
      });
      options.activeInspectionMode.value = "questions";
    } catch (error) {
      console.error("Exam Converter teacher correction apply failed.", error);
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

  return {
    applyItemTextPatch,
    applyManualAnswerKey,
    applyPointCorrection,
    isCorrectionApplying,
  };
}
