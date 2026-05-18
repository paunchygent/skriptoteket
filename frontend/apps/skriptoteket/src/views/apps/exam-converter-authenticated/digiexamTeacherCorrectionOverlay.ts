/**
 * DigiExam teacher correction overlay builder.
 *
 * Domain purpose:
 *   Build source-bound Sir Convert correction entries from producer-issued
 *   source state before PDF/QTI artifacts are used.
 *
 * Relationships:
 *   - Consumes question rows from the Exam Converter review projection.
 *   - Produces unified Exam Authoring correction/apply payloads for the
 *     authenticated Sir Convert Gateway client.
 *   - Keeps correction overlays separate from advisory AI-facit review state
 *     and accepted-current-state export decisions.
 */

import type {
  ExamAuthoringCorrectionSourceItem,
  ExamAuthoringCorrectionSourceStateIssueResult,
  ExamAuthoringCorrectionsApplyRequest,
  ExamAuthoringNonMatchingCorrectionEntry,
} from "../../../api/sirConvertGateway";
import {
  DIGIEXAM_ITEM_TYPE_GAP_FILL,
  DIGIEXAM_ITEM_TYPE_MULTIPLE_CHOICE,
  DIGIEXAM_ITEM_TYPE_MULTIPLE_RESPONSE,
  DIGIEXAM_ITEM_TYPE_SINGLE_CHOICE,
} from "../../../api/sirConvertGateway/contractValues";
import type {
  ExamConverterQuestionReviewRow,
  ExamConverterReviewProjection,
} from "./digiexamIrReviewParser";

export type ExamConverterManualAnswerKeyCorrection =
  | {
      correctAlternativeIds: number[];
      kind: "choice";
    }
  | {
      gapAnswers: {
        acceptedValues: string[];
        gapId: string;
      }[];
      kind: "gap_fill";
    };

export type ExamConverterItemTextPatchCorrection = {
  field: "item_title" | "prompt_html" | "prompt_lines";
  value: string;
};

type CorrectionSourceContext = {
  sourceState: ExamAuthoringCorrectionSourceStateIssueResult;
};

function assertValidPointCorrection(maxScore: number): void {
  if (!Number.isInteger(maxScore) || maxScore <= 0) {
    throw new Error("Point correction requires a positive integer score.");
  }
}

function assertSourceItemFingerprint(question: ExamConverterQuestionReviewRow): string {
  if (!question.sourceItemFingerprint) {
    throw new Error("Teacher correction overlay requires source item fingerprints.");
  }
  return question.sourceItemFingerprint;
}

function assertChoiceItem(question: ExamConverterQuestionReviewRow): void {
  if (
    question.itemType !== DIGIEXAM_ITEM_TYPE_MULTIPLE_CHOICE &&
    question.itemType !== DIGIEXAM_ITEM_TYPE_MULTIPLE_RESPONSE &&
    question.itemType !== DIGIEXAM_ITEM_TYPE_SINGLE_CHOICE
  ) {
    throw new Error("Choice answer-key correction requires a choice item.");
  }
}

function assertGapFillItem(question: ExamConverterQuestionReviewRow): void {
  if (question.itemType !== DIGIEXAM_ITEM_TYPE_GAP_FILL) {
    throw new Error("Gap-fill answer-key correction requires a gap-fill item.");
  }
}

function normalizedChoiceIds(correctAlternativeIds: number[]): number[] {
  const normalized = [...new Set(correctAlternativeIds)].sort((left, right) => left - right);
  if (normalized.length === 0 || normalized.some((id) => !Number.isInteger(id) || id <= 0)) {
    throw new Error("Choice answer-key correction requires one or more alternative ids.");
  }
  return normalized;
}

function normalizedGapAnswers(params: {
  gapAnswers: Extract<ExamConverterManualAnswerKeyCorrection, { kind: "gap_fill" }>["gapAnswers"];
  question: ExamConverterQuestionReviewRow;
}) {
  const expectedGapIds = new Set(params.question.gaps.map((gap) => gap.id));
  const normalized = params.gapAnswers.map((gapAnswer) => ({
    accepted_values: [...new Set(gapAnswer.acceptedValues.map((value) => value.trim()))].filter(
      (value) => value.length > 0,
    ),
    gap_id: gapAnswer.gapId.trim(),
  }));
  const submittedGapIds = normalized.map((gapAnswer) => gapAnswer.gap_id);
  if (
    normalized.length === 0 ||
    normalized.length !== expectedGapIds.size ||
    normalized.some((gapAnswer) => gapAnswer.gap_id.length === 0) ||
    normalized.some((gapAnswer) => gapAnswer.accepted_values.length === 0) ||
    submittedGapIds.some((gapId) => !expectedGapIds.has(gapId)) ||
    new Set(submittedGapIds).size !== submittedGapIds.length
  ) {
    throw new Error("Gap-fill answer-key correction requires accepted values for each source gap.");
  }
  return normalized;
}

function sourceItemForQuestion(params: {
  question: ExamConverterQuestionReviewRow;
  sourceState: ExamAuthoringCorrectionSourceStateIssueResult;
}): ExamAuthoringCorrectionSourceItem {
  const sourceItem = params.sourceState.source_authoring_state.items.find(
    (item) => item.item_id === params.question.itemId,
  );
  if (!sourceItem) {
    throw new Error("Teacher correction requires producer-issued source state for the item.");
  }
  if (sourceItem.sequence !== params.question.sequence) {
    throw new Error("Teacher correction source state has a stale item sequence.");
  }
  if (sourceItem.source_item_fingerprint !== assertSourceItemFingerprint(params.question)) {
    throw new Error("Teacher correction source state has a stale item fingerprint.");
  }
  return sourceItem;
}

function baseEntry(params: {
  question: ExamConverterQuestionReviewRow;
  sourceState: ExamAuthoringCorrectionSourceStateIssueResult;
  suffix: string;
}) {
  const sourceItem = sourceItemForQuestion({
    question: params.question,
    sourceState: params.sourceState,
  });
  return {
    entry_id: `corr-${params.suffix}-${params.question.itemId}`,
    item_id: sourceItem.item_id,
    item_type: sourceItem.item_type,
    sequence: sourceItem.sequence,
    source_item_fingerprint: sourceItem.source_item_fingerprint ?? null,
  };
}

function choiceInteractionForQuestion(params: {
  question: ExamConverterQuestionReviewRow;
  sourceState: ExamAuthoringCorrectionSourceStateIssueResult;
}) {
  const sourceItem = sourceItemForQuestion(params);
  const [interaction] = sourceItem.choice_interactions;
  if (!interaction) {
    throw new Error("Choice answer-key correction requires producer choice state.");
  }
  return interaction;
}

function gapInteractionForQuestion(params: {
  question: ExamConverterQuestionReviewRow;
  sourceState: ExamAuthoringCorrectionSourceStateIssueResult;
}) {
  const sourceItem = sourceItemForQuestion(params);
  const [interaction] = sourceItem.gap_open_cloze_interactions;
  if (!interaction) {
    throw new Error("Gap-fill answer-key correction requires producer gap state.");
  }
  return interaction;
}

function sourceChoiceIdForDisplayId(params: {
  displayId: number;
  question: ExamConverterQuestionReviewRow;
  sourceState: ExamAuthoringCorrectionSourceStateIssueResult;
}): string {
  const interaction = choiceInteractionForQuestion(params);
  const displayId = String(params.displayId);
  const choice = interaction.choices.find(
    (candidate) => candidate.source_id === displayId || candidate.order === params.displayId,
  );
  if (!choice) {
    throw new Error("Choice answer-key correction references an unknown producer choice.");
  }
  return choice.choice_id;
}

function pointCorrectionEntry(params: {
  entrySuffix: string;
  maxScore: number;
  question: ExamConverterQuestionReviewRow;
  sourceState: ExamAuthoringCorrectionSourceStateIssueResult;
}): ExamAuthoringNonMatchingCorrectionEntry {
  return {
    ...baseEntry({
      question: params.question,
      sourceState: params.sourceState,
      suffix: params.entrySuffix,
    }),
    kind: "point_correction",
    max_score: params.maxScore,
  };
}

function choiceAnswerKeyEntry(params: {
  correctAlternativeIds: number[];
  entrySuffix: string;
  question: ExamConverterQuestionReviewRow;
  sourceState: ExamAuthoringCorrectionSourceStateIssueResult;
}): ExamAuthoringNonMatchingCorrectionEntry {
  assertChoiceItem(params.question);
  return {
    ...baseEntry({
      question: params.question,
      sourceState: params.sourceState,
      suffix: params.entrySuffix,
    }),
    candidate_lineage: null,
    correct_choice_ids: normalizedChoiceIds(params.correctAlternativeIds).map((displayId) =>
      sourceChoiceIdForDisplayId({
        displayId,
        question: params.question,
        sourceState: params.sourceState,
      }),
    ),
    interaction_id: choiceInteractionForQuestion({
      question: params.question,
      sourceState: params.sourceState,
    }).interaction_id,
    kind: "manual_choice_answer_key",
    submission_origin: "teacher_authored",
  };
}

function gapAnswerKeyEntry(params: {
  entrySuffix: string;
  gapAnswers: Extract<ExamConverterManualAnswerKeyCorrection, { kind: "gap_fill" }>["gapAnswers"];
  question: ExamConverterQuestionReviewRow;
  sourceState: ExamAuthoringCorrectionSourceStateIssueResult;
}): ExamAuthoringNonMatchingCorrectionEntry {
  assertGapFillItem(params.question);
  return {
    ...baseEntry({
      question: params.question,
      sourceState: params.sourceState,
      suffix: params.entrySuffix,
    }),
    candidate_lineage: null,
    gap_answers: normalizedGapAnswers({
      gapAnswers: params.gapAnswers,
      question: params.question,
    }),
    interaction_id: gapInteractionForQuestion({
      question: params.question,
      sourceState: params.sourceState,
    }).interaction_id,
    kind: "manual_gap_open_cloze_answer_key",
    submission_origin: "teacher_authored",
  };
}

function itemTextPatchEntry(params: {
  entrySuffix: string;
  patches: { field: ExamConverterItemTextPatchCorrection["field"]; value: string }[];
  question: ExamConverterQuestionReviewRow;
  sourceState: ExamAuthoringCorrectionSourceStateIssueResult;
}): ExamAuthoringNonMatchingCorrectionEntry {
  return {
    ...baseEntry({
      question: params.question,
      sourceState: params.sourceState,
      suffix: params.entrySuffix,
    }),
    kind: "item_text_patch",
    patches: params.patches,
  };
}

function correctionRequest(params: {
  correction: ExamAuthoringNonMatchingCorrectionEntry;
  projection: ExamConverterReviewProjection;
  sourceState: ExamAuthoringCorrectionSourceStateIssueResult;
}): ExamAuthoringCorrectionsApplyRequest {
  return {
    schema_version: "exam_authoring_corrections_apply_request_v1",
    request_id: `correction-${params.correction.kind}-${params.correction.item_id}`,
    source_binding: params.sourceState.source_binding,
    source_authoring_state: params.sourceState.source_authoring_state,
    corrections: [params.correction],
    requested_targets: params.projection.files
      .map((file) => file.artifactKey)
      .filter((artifactKey): artifactKey is "examnet_pdf" | "qti_package" =>
        artifactKey === "examnet_pdf" || artifactKey === "qti_package",
      ),
  };
}

export function buildPointCorrectionRequest(params: {
  maxScore: number;
  projection: ExamConverterReviewProjection;
  question: ExamConverterQuestionReviewRow;
} & CorrectionSourceContext): ExamAuthoringCorrectionsApplyRequest {
  assertValidPointCorrection(params.maxScore);
  return correctionRequest({
    projection: params.projection,
    sourceState: params.sourceState,
    correction: pointCorrectionEntry({
      entrySuffix: "points",
      maxScore: params.maxScore,
      question: params.question,
      sourceState: params.sourceState,
    }),
  });
}

export function buildManualAnswerKeyRequest(params: {
  answerKey: ExamConverterManualAnswerKeyCorrection;
  projection: ExamConverterReviewProjection;
  question: ExamConverterQuestionReviewRow;
} & CorrectionSourceContext): ExamAuthoringCorrectionsApplyRequest {
  const correction: ExamAuthoringNonMatchingCorrectionEntry =
    params.answerKey.kind === "choice"
      ? choiceAnswerKeyEntry({
          correctAlternativeIds: params.answerKey.correctAlternativeIds,
          entrySuffix: "manual-choice",
          question: params.question,
          sourceState: params.sourceState,
        })
      : gapAnswerKeyEntry({
          entrySuffix: "manual-gap",
          gapAnswers: params.answerKey.gapAnswers,
          question: params.question,
          sourceState: params.sourceState,
        });
  return correctionRequest({
    correction,
    projection: params.projection,
    sourceState: params.sourceState,
  });
}

export function buildItemTextPatchRequest(params: {
  patch: ExamConverterItemTextPatchCorrection;
  projection: ExamConverterReviewProjection;
  question: ExamConverterQuestionReviewRow;
} & CorrectionSourceContext): ExamAuthoringCorrectionsApplyRequest {
  const value = params.patch.value.trim();
  if (value.length === 0) {
    throw new Error("Item text correction requires a non-empty value.");
  }
  return correctionRequest({
    projection: params.projection,
    sourceState: params.sourceState,
    correction: itemTextPatchEntry({
      entrySuffix: "text",
      patches: [{ field: params.patch.field, value }],
      question: params.question,
      sourceState: params.sourceState,
    }),
  });
}
