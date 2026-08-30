/**
 * Exam Converter correction-session projection.
 *
 * Domain purpose:
 *   Convert fresh local replay results into the authenticated Exam
 *   Converter review projection shown to teachers.
 *
 * Relationships:
 *   - Consumed by `useExamConverterUnifiedCorrections` after persisted intent
 *     replay.
 *   - Preserves question, file, and readiness display state as replayed truth.
 */

import type {
  ExamConverterCorrectionIntentResponse,
  ExamConverterCorrectionSessionResponse,
} from "../../../api/examConverterCorrectionSessions";
import type {
  DigiExamAnswerKeyReviewReplayArtifactReference,
  DigiExamEffectiveAnswerKey,
  ExamAuthoringCorrectionSourceItem,
  ExamAuthoringCorrectionSourceStateIssueResult,
  ExamAuthoringCorrectionsApplyResult,
} from "../../../api/examConverterContracts";
import type {
  ExamConverterQuestionReviewRow,
  ExamConverterReviewFileActionReference,
  ExamConverterReviewFile,
  ExamConverterReviewProjection,
} from "./digiexamIrReviewParser";
import { buildAiSuggestionReport, hasUsableCompletionCandidate } from "./digiexamIrReviewParser";
import { DIGIEXAM_ITEM_TYPE_OPEN_ENDED } from "../../../api/examConverterContracts";
import {
  applyAnswerKeyReviewStateToQuestions,
  parseAnswerKeyReviewState,
} from "./answerKeyReviewStateAdapter";

type JsonRecord = Record<string, unknown>;

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
}): DigiExamEffectiveAnswerKey | null {
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

function savedAnswerKeyForIntent(params: {
  intent: ExamConverterCorrectionIntentResponse | undefined;
  sourceItem: ExamAuthoringCorrectionSourceItem | null;
}): DigiExamEffectiveAnswerKey | null {
  const { intent, sourceItem } = params;
  if (!intent) return null;
  if (intent.kind === "manual_choice_answer_key") {
    const choices = sourceItem?.choice_interactions[0]?.choices ?? [];
    const correctChoiceIds = Array.isArray(intent.payload.correct_choice_ids)
      ? intent.payload.correct_choice_ids
      : [];
    const correctAlternativeIds = correctChoiceIds
      .map((choiceId) =>
        choices.find((choice) => choice.choice_id === choiceId),
      )
      .map(displayIdForSourceChoice)
      .filter(isIntegerChoiceId);
    if (correctAlternativeIds.length === 0) return null;
    return {
      correct_alternative_ids: correctAlternativeIds,
      lineage: null,
      provenance: savedAnswerKeyProvenance(intent),
    };
  }
  if (intent.kind === "manual_gap_open_cloze_answer_key") {
    const gapAnswers = Array.isArray(intent.payload.gap_answers)
      ? intent.payload.gap_answers
      : [];
    const correctGapAnswers = gapAnswers.flatMap((gapAnswer): Record<string, string>[] => {
      if (!isJsonRecord(gapAnswer)) {
        return [];
      }
      const gapId = "gap_id" in gapAnswer ? String(gapAnswer.gap_id) : "";
      const acceptedValues =
        "accepted_values" in gapAnswer && Array.isArray(gapAnswer.accepted_values)
          ? gapAnswer.accepted_values
          : [];
      return acceptedValues
        .filter((value): value is string => typeof value === "string" && value.trim().length > 0)
        .map((value: string) => ({ [gapId]: value }));
    });
    if (correctGapAnswers.length === 0) return null;
    return {
      correct_gap_answers: correctGapAnswers,
      lineage: null,
      provenance: savedAnswerKeyProvenance(intent),
    };
  }
  return null;
}

function savedAnswerKeyProvenance(intent: ExamConverterCorrectionIntentResponse): string {
  return intent.payload.submission_origin === "accepted_advisory_candidate"
    ? "accepted_advisory_candidate"
    : "teacher_provided";
}

function isJsonRecord(value: unknown): value is JsonRecord {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function savedAnswerKeyIntentsByItem(
  intents: ExamConverterCorrectionIntentResponse[],
): Map<string, ExamConverterCorrectionIntentResponse> {
  return new Map(
    intents
      .filter(
        (intent) =>
          intent.kind === "manual_choice_answer_key" ||
          intent.kind === "manual_gap_open_cloze_answer_key",
      )
      .map((intent) => [intent.item_id, intent]),
  );
}

function savedPointCorrectionForIntent(params: {
  intent: ExamConverterCorrectionIntentResponse | undefined;
  question: ExamConverterQuestionReviewRow;
}): ExamConverterQuestionReviewRow["effectivePointCorrection"] {
  const { intent, question } = params;
  if (!intent || intent.kind !== "point_correction") return null;
  const maxScore =
    typeof intent.payload.max_score === "number" ? intent.payload.max_score : null;
  if (maxScore === null || maxScore === question.pointsValue) return null;
  return {
    effective_max_score: maxScore,
    kind: "item_points",
    source_item_fingerprint: question.sourceItemFingerprint ?? "",
    source_max_score: question.pointsValue,
  };
}

function savedPointIntentsByItem(
  intents: ExamConverterCorrectionIntentResponse[],
): Map<string, ExamConverterCorrectionIntentResponse> {
  return new Map(
    intents
      .filter((intent) => intent.kind === "point_correction")
      .map((intent) => [intent.item_id, intent]),
  );
}

function savedTextPatchValue(params: {
  field: "item_title" | "prompt_lines";
  intent: ExamConverterCorrectionIntentResponse | undefined;
}): string | null {
  const { field, intent } = params;
  if (!intent || intent.kind !== "item_text_patch" || !Array.isArray(intent.payload.patches)) {
    return null;
  }
  const patch = intent.payload.patches.find(
    (entry): entry is JsonRecord =>
      isJsonRecord(entry) && entry.field === field && typeof entry.value === "string",
  );
  return typeof patch?.value === "string" && patch.value.trim().length > 0
    ? patch.value
    : null;
}

function savedTextPatchIntentsByItem(
  intents: ExamConverterCorrectionIntentResponse[],
): Map<string, ExamConverterCorrectionIntentResponse[]> {
  const grouped = new Map<string, ExamConverterCorrectionIntentResponse[]>();
  for (const intent of intents) {
    if (intent.kind !== "item_text_patch") continue;
    grouped.set(intent.item_id, [...(grouped.get(intent.item_id) ?? []), intent]);
  }
  return grouped;
}

function savedTextValue(params: {
  field: "item_title" | "prompt_lines";
  intents: ExamConverterCorrectionIntentResponse[] | undefined;
}): string | null {
  for (const intent of params.intents ?? []) {
    const value = savedTextPatchValue({ field: params.field, intent });
    if (value) return value;
  }
  return null;
}

function correctedMissingFields(params: {
  effectiveAnswerKey: ReturnType<typeof effectiveAnswerKeyForSourceItem>;
  effectivePointCorrection: ExamConverterQuestionReviewRow["effectivePointCorrection"];
  question: ExamConverterQuestionReviewRow;
}): ExamConverterQuestionReviewRow["missingFields"] {
  const fields = new Set(params.question.missingFields);
  if (params.effectivePointCorrection) {
    fields.delete("Poäng");
  } else if (params.question.pointsValue === null) {
    fields.add("Poäng");
  }
  if (params.effectiveAnswerKey) {
    fields.delete("Facit");
  } else if (params.question.itemType !== DIGIEXAM_ITEM_TYPE_OPEN_ENDED) {
    fields.add("Facit");
  }
  return [...fields];
}

function reportForCorrectedQuestions(
  projection: ExamConverterReviewProjection,
  questions: ExamConverterQuestionReviewRow[],
  files: ExamConverterReviewFile[],
  aiSuggestionOutcomes: ReturnType<typeof savedAiSuggestionOutcomeItemIds>,
) {
  return {
    ...projection.report,
    aiSuggestionOutcomes: buildAiSuggestionReport({
      acceptedUnchangedItemIds: aiSuggestionOutcomes.acceptedUnchangedItemIds,
      questions,
      suppressedItemIds: aiSuggestionOutcomes.suppressedItemIds,
      teacherEditedItemIds: aiSuggestionOutcomes.teacherEditedItemIds,
    }),
    aiSuggestionCount: questions.filter(hasUsableCompletionCandidate).length,
    blockedTargetFileCount: files.filter((file) => !file.exportEnabled).length,
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

type CorrectionTargetReadinessRow =
  ExamAuthoringCorrectionsApplyResult["target_readiness"]["targets"][number];

function correctedFileStatusLabel(params: {
  file: ExamConverterReviewFile;
  replayExportEnabled: boolean;
}): string {
  const { file, replayExportEnabled } = params;
  if (file.exportEnabled && file.artifactActionReference) return "Kan hämtas";
  if (replayExportEnabled && !file.artifactActionReference) return "Filer kunde inte skapas";
  if (file.availability === "available") return "Granska facit först";
  return "Kunde inte skapas";
}

function replayArtifactActionReference(params: {
  availability: ExamAuthoringCorrectionsApplyResult["artifact_availability"][number] | undefined;
  replayReference: DigiExamAnswerKeyReviewReplayArtifactReference | undefined;
  readinessRows: CorrectionTargetReadinessRow[];
}): ExamConverterReviewFileActionReference | null {
  const readinessRow = params.readinessRows.find((row) => row.export_enabled) ?? null;
  if (!readinessRow || params.availability?.availability !== "available") return null;
  if (!params.replayReference) return null;
  return {
    artifactKey: params.replayReference.artifact_key,
    artifactSetId: params.replayReference.artifact_set_id,
    authority: "replay_result",
    contentSha256: params.replayReference.content_sha256,
    jobId: params.replayReference.job_id,
    replayArtifactReference: params.replayReference,
  };
}

function replayReferencesByTarget(
  result: ExamAuthoringCorrectionsApplyResult,
): Map<string, DigiExamAnswerKeyReviewReplayArtifactReference> {
  const references = new Map<string, DigiExamAnswerKeyReviewReplayArtifactReference>();
  for (const item of result.answer_key_review_state.items) {
    for (const reference of item.replay_artifact_references) {
      references.set(reference.target, reference);
    }
  }
  return references;
}

function projectCorrectedFiles(
  projection: ExamConverterReviewProjection,
  result: ExamAuthoringCorrectionsApplyResult,
): ExamConverterReviewFile[] {
  const replayReferences = replayReferencesByTarget(result);
  return projection.files.map((file) => {
    const availabilityRow = result.artifact_availability.find(
      (entry) => entry.artifact_key === file.artifactKey,
    );
    const readinessRows = result.target_readiness.targets.filter(
      (row) => row.target === file.artifactKey,
    );
    const readinessRow = readinessRows.find((row) => !row.export_enabled) ?? readinessRows[0] ?? null;
    const availability = availabilityRow?.availability ?? "unavailable";
    const replayExportEnabled =
      availability === "available" && readinessRows.some((row) => row.export_enabled);
    const artifactActionReference = replayArtifactActionReference({
      availability: availabilityRow,
      replayReference: replayReferences.get(file.artifactKey),
      readinessRows,
    });
    const exportEnabled = replayExportEnabled && artifactActionReference !== null;
    const correctedFile = {
      ...file,
      artifactActionReference,
      availability,
      exportEnabled,
      reasonCode: readinessRow?.reason_code ?? availabilityRow?.unavailable_code ?? file.reasonCode,
      readiness: readinessRow?.readiness ?? file.readiness,
      unavailableCode: availabilityRow?.unavailable_code ?? file.unavailableCode,
    };
    return {
      ...correctedFile,
      statusLabel: correctedFileStatusLabel({ file: correctedFile, replayExportEnabled }),
    };
  });
}

function suppressedCandidateItemIds(result: ExamAuthoringCorrectionsApplyResult): Set<string> {
  return new Set(
    result.correction_report.accepted_entries
      .filter((entry) => entry.kind === "candidate_suppression")
      .map((entry) => entry.item_id),
  );
}

function savedSuppressedCandidateItemIds(
  intents: ExamConverterCorrectionIntentResponse[],
): Set<string> {
  return new Set(
    intents
      .filter((intent) => intent.kind === "candidate_suppression")
      .map((intent) => intent.item_id),
  );
}

function savedAiSuggestionOutcomeItemIds(
  intents: ExamConverterCorrectionIntentResponse[],
): {
  acceptedUnchangedItemIds: Set<string>;
  suppressedItemIds: Set<string>;
  teacherEditedItemIds: Set<string>;
} {
  const acceptedUnchangedItemIds = new Set<string>();
  const teacherEditedItemIds = new Set<string>();
  for (const intent of intents) {
    if (
      intent.kind !== "manual_choice_answer_key" &&
      intent.kind !== "manual_gap_open_cloze_answer_key"
    ) {
      continue;
    }
    if (intent.payload.submission_origin === "accepted_advisory_candidate") {
      acceptedUnchangedItemIds.add(intent.item_id);
    }
    if (intent.payload.submission_origin === "teacher_edited_advisory_candidate") {
      teacherEditedItemIds.add(intent.item_id);
    }
  }
  return {
    acceptedUnchangedItemIds,
    suppressedItemIds: savedSuppressedCandidateItemIds(intents),
    teacherEditedItemIds,
  };
}

export function projectUnifiedCorrectionResult(params: {
  correctionSession: ExamConverterCorrectionSessionResponse;
  projection: ExamConverterReviewProjection;
  result: ExamAuthoringCorrectionsApplyResult;
  sourceState: ExamAuthoringCorrectionSourceStateIssueResult;
}): ExamConverterReviewProjection {
  const suppressedItems = new Set([
    ...suppressedCandidateItemIds(params.result),
    ...savedSuppressedCandidateItemIds(params.correctionSession.active_intents),
  ]);
  const aiSuggestionOutcomes = savedAiSuggestionOutcomeItemIds(
    params.correctionSession.active_intents,
  );
  for (const itemId of suppressedCandidateItemIds(params.result)) {
    aiSuggestionOutcomes.suppressedItemIds.add(itemId);
  }
  const savedAnswerKeysByItem = savedAnswerKeyIntentsByItem(
    params.correctionSession.active_intents,
  );
  const savedPointsByItem = savedPointIntentsByItem(params.correctionSession.active_intents);
  const savedTextByItem = savedTextPatchIntentsByItem(params.correctionSession.active_intents);
  const effectiveItemsById = new Map(
    params.result.effective_state.items.map((item) => [item.item_id, item]),
  );
  const sourceItemsById = new Map(
    params.sourceState.source_authoring_state.items.map((item) => [item.item_id, item]),
  );
  const locallyProjectedQuestions = params.projection.questions.map((question): ExamConverterQuestionReviewRow => {
    const effectiveItem = effectiveItemsById.get(question.itemId);
    if (!effectiveItem) return question;
    const sourceItem = sourceItemsById.get(question.itemId) ?? null;
    const effectiveMaxScore =
      typeof effectiveItem.max_score === "number" ? effectiveItem.max_score : null;
    const replayedPointCorrection =
      effectiveMaxScore === question.pointsValue || effectiveMaxScore === null
        ? question.effectivePointCorrection
        : {
            effective_max_score: effectiveMaxScore,
            kind: "item_points" as const,
            source_item_fingerprint: question.sourceItemFingerprint ?? "",
            source_max_score: question.pointsValue,
          };
    const savedPointCorrection = savedPointCorrectionForIntent({
      intent: savedPointsByItem.get(question.itemId),
      question,
    });
    const effectivePointCorrection = savedPointCorrection ?? replayedPointCorrection;
    const effectiveAnswerKey =
      savedAnswerKeyForIntent({
        intent: savedAnswerKeysByItem.get(question.itemId),
        sourceItem,
      }) ?? effectiveAnswerKeyForSourceItem({ effectiveItem, sourceItem });
    const pointsValue =
      effectivePointCorrection?.effective_max_score ?? effectiveMaxScore ?? question.pointsValue;
    const missingFields = correctedMissingFields({
      effectiveAnswerKey,
      effectivePointCorrection,
      question,
    });
    const llmCandidate =
      effectiveAnswerKey || suppressedItems.has(question.itemId) ? null : question.llmCandidate;
    return {
      ...question,
      currentAnswerKeyProvenance:
        effectiveAnswerKey?.provenance ?? question.currentAnswerKeyProvenance,
      effectiveAnswerKey,
      effectivePointCorrection,
      llmCandidate: savedAnswerKeysByItem.has(question.itemId) ? null : llmCandidate,
      missingFields,
      pointsLabel: pointsValue === null ? "—" : `${pointsValue.toLocaleString("sv-SE")} p`,
      pointsValue,
      promptText:
        savedTextValue({ field: "prompt_lines", intents: savedTextByItem.get(question.itemId) }) ??
        (promptTextForSourceItem(effectiveItem) || question.promptText),
      status: missingFields.length > 0 ? question.status : "complete",
      statusSymbol: missingFields.includes("Facit") && question.itemType !== "open_ended"
        ? "validation_required"
        : "complete",
      title:
        savedTextValue({ field: "item_title", intents: savedTextByItem.get(question.itemId) }) ??
        effectiveItem.title ??
        question.title,
    };
  });
  const replayReviewState = parseAnswerKeyReviewState(params.result.answer_key_review_state);
  const questions = applyAnswerKeyReviewStateToQuestions({
    questions: locallyProjectedQuestions,
    reviewState: replayReviewState,
  });
  const files = projectCorrectedFiles(params.projection, {
    ...params.result,
    answer_key_review_state: replayReviewState,
  });
  return {
    ...params.projection,
    files,
    questions,
    report: reportForCorrectedQuestions(
      params.projection,
      questions,
      files,
      aiSuggestionOutcomes,
    ),
  };
}
