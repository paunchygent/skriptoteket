/**
 * DigiExam IR question review projection.
 *
 * Domain purpose:
 *   Convert one validated Sir Convert DigiExam IR item into a read-only
 *   teacher-facing question row for authenticated Exam Converter review.
 *
 * Relationships:
 *   - Receives validated item structures from `digiexamIrReviewParser`.
 *   - Owns question type labels, missing-field labels, flerval alternatives,
 *     and Lucktext structure for the review pane.
 *   - Does not mutate IR, infer answers, or create local review state.
 */

import type {
  DigiExamEffectiveAnswerKey,
  DigiExamEffectivePointCorrection,
  DigiExamItemType,
} from "../../../api/sirConvertGateway";
import {
  DIGIEXAM_ITEM_TYPE_GAP_FILL,
  DIGIEXAM_ITEM_TYPE_MULTIPLE_CHOICE,
  DIGIEXAM_ITEM_TYPE_MULTIPLE_RESPONSE,
  DIGIEXAM_ITEM_TYPE_OPEN_ENDED,
  DIGIEXAM_ITEM_TYPE_SINGLE_CHOICE,
  DIGIEXAM_MANUAL_FOLLOW_UP_MANUAL_ANSWER_KEY_REQUIRED,
  DIGIEXAM_MANUAL_FOLLOW_UP_PARSER_WARNING_BLOCKS_RENDERING,
  DIGIEXAM_MANUAL_FOLLOW_UP_UNSUPPORTED_ITEM_TYPE,
} from "../../../api/sirConvertGateway/contractValues";
import type { ExamConverterLlmAnswerKeyCandidate } from "./digiexamAnswerKeyCompletionReport";

export type ExamConverterMissingFieldLabel = "Facit" | "Poäng";
export type ExamConverterQuestionReviewStatus = "complete" | "attention";
export type ExamConverterQuestionStatusSymbol =
  | "ai_suggestion"
  | "complete"
  | "teacher_modified"
  | "validation_required";

export type ExamConverterQuestionAlternative = {
  id: string;
  text: string;
};

export type ExamConverterLucktextImage = {
  id: string;
  altText: string;
  dataUrl: string | null;
  dimensionsLabel: string | null;
};

export type ExamConverterLucktextStructure = {
  gapCount: number;
  imageCount: number;
  images: ExamConverterLucktextImage[];
};

export type ExamConverterQuestionGap = {
  id: string;
  label: string;
};

export type ExamConverterQuestionReviewRow = {
  itemId: string;
  itemType: DigiExamItemType;
  sequence: number;
  sourceItemFingerprint: string | null;
  title: string;
  typeLabel: string;
  pointsValue: number | null;
  pointsLabel: string;
  promptText: string;
  missingFields: ExamConverterMissingFieldLabel[];
  status: ExamConverterQuestionReviewStatus;
  statusSymbol: ExamConverterQuestionStatusSymbol;
  answerKeyReviewOrigin: string | null;
  answerKeyReviewReasons: string[];
  answerKeyReviewState: string | null;
  answerKeyReviewStateLabel: string;
  answerKeyReviewStateReasonLabel: string | null;
  currentAnswerKeyProvenance: string;
  effectiveAnswerKey: DigiExamEffectiveAnswerKey | null;
  effectivePointCorrection: DigiExamEffectivePointCorrection | null;
  llmCandidate: ExamConverterLlmAnswerKeyCandidate | null;
  manualFollowUpMessages: string[];
  alternatives: ExamConverterQuestionAlternative[];
  gaps: ExamConverterQuestionGap[];
  lucktextStructure: ExamConverterLucktextStructure | null;
};

export type DigiExamIrAnswerKey = {
  provenance: string;
};

export type DigiExamIrAlternative = {
  id: number;
  title: string;
  about: string;
};

export type DigiExamIrEmbeddedAsset = {
  assetId: string;
  mediaType: string;
  contentBase64: string | null;
  sourceImageIndex: number;
  widthPx: number | null;
  heightPx: number | null;
};

export type DigiExamIrEmbeddedAssetReference = {
  assetId: string;
  sourceImageIndex: number;
  referenceOrder: number;
};

export type DigiExamIrGap = {
  id: string;
};

export type DigiExamIrManualFollowUp = {
  itemId: string;
  reason: string;
  message: string;
};

export type DigiExamIrItem = {
  itemId: string;
  sequence: number;
  title: string;
  itemType: DigiExamItemType;
  promptHtml: string | null;
  promptLines: string[];
  maxScore: number | null;
  answerKey: DigiExamIrAnswerKey;
  warnings: Record<string, unknown>[];
  options: string[];
  alternatives: DigiExamIrAlternative[];
  gaps: DigiExamIrGap[];
  embeddedAssets: DigiExamIrEmbeddedAsset[];
  embeddedAssetReferences: DigiExamIrEmbeddedAssetReference[];
};

function stripHtml(value: string): string {
  return value.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();
}

function promptTextForItem(item: DigiExamIrItem): string {
  const joinedLines = item.promptLines.join(" ").trim();
  if (joinedLines.length > 0) {
    return joinedLines;
  }
  if (item.promptHtml) {
    return stripHtml(item.promptHtml);
  }
  return item.title;
}

function typeLabelForItemType(itemType: string): string {
  switch (itemType) {
    case DIGIEXAM_ITEM_TYPE_GAP_FILL:
      return "Lucktext";
    case DIGIEXAM_ITEM_TYPE_MULTIPLE_CHOICE:
    case DIGIEXAM_ITEM_TYPE_SINGLE_CHOICE:
    case DIGIEXAM_ITEM_TYPE_MULTIPLE_RESPONSE:
      return "Flerval";
    case DIGIEXAM_ITEM_TYPE_OPEN_ENDED:
      return "Fritext";
    default:
      return "Okänd";
  }
}

export function isAnswerKeyReviewableItemType(itemType: string): boolean {
  return (
    itemType === DIGIEXAM_ITEM_TYPE_GAP_FILL ||
    itemType === DIGIEXAM_ITEM_TYPE_MULTIPLE_CHOICE ||
    itemType === DIGIEXAM_ITEM_TYPE_SINGLE_CHOICE ||
    itemType === DIGIEXAM_ITEM_TYPE_MULTIPLE_RESPONSE
  );
}

export function isOpenResponseItemType(itemType: string): boolean {
  return itemType === DIGIEXAM_ITEM_TYPE_OPEN_ENDED;
}

function alternativeText(alternative: DigiExamIrAlternative): string {
  return stripHtml([alternative.title, alternative.about].filter(Boolean).join(" ")).trim();
}

function projectAlternatives(item: DigiExamIrItem): ExamConverterQuestionAlternative[] {
  if (item.alternatives.length > 0) {
    return item.alternatives
      .map((alternative) => ({
        id: alternative.id.toLocaleString("sv-SE"),
        text: alternativeText(alternative),
      }))
      .filter((alternative) => alternative.text.length > 0);
  }

  if (item.options.length > 0) {
    return item.options
      .map((option, index) => ({
        id: (index + 1).toLocaleString("sv-SE"),
        text: stripHtml(option),
      }))
      .filter((alternative) => alternative.text.length > 0);
  }

  return [];
}

function projectGaps(item: DigiExamIrItem): ExamConverterQuestionGap[] {
  return item.gaps.map((gap, index) => ({
    id: gap.id,
    label: `Lucka ${index + 1}`,
  }));
}

function countPromptHtmlMatches(promptHtml: string | null, pattern: RegExp): number {
  if (!promptHtml) return 0;
  return [...promptHtml.matchAll(pattern)].length;
}

function gapCountForItem(item: DigiExamIrItem): number {
  if (item.gaps.length > 0) {
    return item.gaps.length;
  }
  return countPromptHtmlMatches(item.promptHtml, /\bdx-wg-id\s*=/g);
}

function imageCountForItem(item: DigiExamIrItem): number {
  if (item.embeddedAssets.length > 0) {
    return item.embeddedAssets.length;
  }
  if (item.embeddedAssetReferences.length > 0) {
    return item.embeddedAssetReferences.length;
  }
  return countPromptHtmlMatches(item.promptHtml, /\bdata-image-id\s*=/g);
}

function dimensionsLabel(asset: DigiExamIrEmbeddedAsset): string | null {
  if (asset.widthPx === null || asset.heightPx === null) {
    return null;
  }
  return `${asset.widthPx.toLocaleString("sv-SE")} × ${asset.heightPx.toLocaleString("sv-SE")} px`;
}

function imageDataUrl(asset: DigiExamIrEmbeddedAsset): string | null {
  if (!asset.contentBase64 || !asset.mediaType.startsWith("image/")) {
    return null;
  }
  return `data:${asset.mediaType};base64,${asset.contentBase64}`;
}

function projectLucktextImages(item: DigiExamIrItem): ExamConverterLucktextImage[] {
  if (item.embeddedAssets.length > 0) {
    return item.embeddedAssets.map((asset, index) => ({
      id: asset.assetId,
      altText: `Bild ${index + 1}`,
      dataUrl: imageDataUrl(asset),
      dimensionsLabel: dimensionsLabel(asset),
    }));
  }

  return item.embeddedAssetReferences.map((reference, index) => ({
    id: reference.assetId,
    altText: `Bild ${index + 1}`,
    dataUrl: null,
    dimensionsLabel: null,
  }));
}

function projectLucktextStructure(item: DigiExamIrItem): ExamConverterLucktextStructure | null {
  if (item.itemType !== DIGIEXAM_ITEM_TYPE_GAP_FILL) {
    return null;
  }
  return {
    gapCount: gapCountForItem(item),
    imageCount: imageCountForItem(item),
    images: projectLucktextImages(item),
  };
}

function uniqueLabels(labels: ExamConverterMissingFieldLabel[]): ExamConverterMissingFieldLabel[] {
  return [...new Set(labels)];
}

function missingFieldsForItem(
  effectivePointCorrection: DigiExamEffectivePointCorrection | null,
  item: DigiExamIrItem,
  followUps: DigiExamIrManualFollowUp[],
): ExamConverterMissingFieldLabel[] {
  const labels: ExamConverterMissingFieldLabel[] = [];
  if (item.maxScore === null && effectivePointCorrection === null) {
    labels.push("Poäng");
  }
  if (
    isAnswerKeyReviewableItemType(item.itemType) &&
    followUps.some(
      (followUp) => followUp.reason === DIGIEXAM_MANUAL_FOLLOW_UP_MANUAL_ANSWER_KEY_REQUIRED,
    )
  ) {
    labels.push("Facit");
  }
  return uniqueLabels(labels);
}

function isActionableFollowUp(
  followUp: DigiExamIrManualFollowUp,
  item: DigiExamIrItem,
): boolean {
  if (isOpenResponseItemType(item.itemType)) {
    return false;
  }
  if (followUp.reason === DIGIEXAM_MANUAL_FOLLOW_UP_MANUAL_ANSWER_KEY_REQUIRED) {
    return isAnswerKeyReviewableItemType(item.itemType);
  }
  return (
    followUp.reason === DIGIEXAM_MANUAL_FOLLOW_UP_UNSUPPORTED_ITEM_TYPE ||
    followUp.reason === DIGIEXAM_MANUAL_FOLLOW_UP_PARSER_WARNING_BLOCKS_RENDERING
  );
}

function hasEffectiveAnswerKey(
  answerKey: DigiExamEffectiveAnswerKey | null | undefined,
): answerKey is DigiExamEffectiveAnswerKey {
  return Boolean(answerKey?.provenance && answerKey.provenance !== "absent");
}

export function isAiAnswerKeyProvenance(provenance: string | null | undefined): boolean {
  return provenance === "accepted_advisory_candidate";
}

function followUpsForEffectiveAnswerKey(params: {
  effectiveAnswerKey: DigiExamEffectiveAnswerKey | null | undefined;
  followUps: DigiExamIrManualFollowUp[];
}): DigiExamIrManualFollowUp[] {
  if (!hasEffectiveAnswerKey(params.effectiveAnswerKey)) {
    return params.followUps;
  }
  return params.followUps.filter(
    (followUp) => followUp.reason !== DIGIEXAM_MANUAL_FOLLOW_UP_MANUAL_ANSWER_KEY_REQUIRED,
  );
}

function isAttentionRow(params: {
  followUps: DigiExamIrManualFollowUp[];
  item: DigiExamIrItem;
  missingFields: ExamConverterMissingFieldLabel[];
}): boolean {
  return (
    params.missingFields.length > 0 ||
    params.followUps.some((followUp) => isActionableFollowUp(followUp, params.item)) ||
    params.item.warnings.length > 0
  );
}

function hasUsableCandidate(candidate: ExamConverterLlmAnswerKeyCandidate | null): boolean {
  return (
    candidate?.decisionState === "suggested" &&
    candidate.validationState === "valid" &&
    candidate.answerPayload !== null
  );
}

function statusSymbolForItem(params: {
  candidate: ExamConverterLlmAnswerKeyCandidate | null;
  effectiveAnswerKey: DigiExamEffectiveAnswerKey | null | undefined;
  item: DigiExamIrItem;
  missingFields: ExamConverterMissingFieldLabel[];
}): ExamConverterQuestionStatusSymbol {
  if (hasUsableCandidate(params.candidate)) {
    return "ai_suggestion";
  }
  if (
    params.missingFields.includes("Facit") &&
    isAnswerKeyReviewableItemType(params.item.itemType)
  ) {
    return "validation_required";
  }
  return "complete";
}

export function projectQuestionReviewRow(
  item: DigiExamIrItem,
  itemFollowUps: DigiExamIrManualFollowUp[],
  sourceItemFingerprint: string | null,
  llmCandidate: ExamConverterLlmAnswerKeyCandidate | null,
  effectiveAnswerKey: DigiExamEffectiveAnswerKey | null = null,
  effectivePointCorrection: DigiExamEffectivePointCorrection | null = null,
): ExamConverterQuestionReviewRow {
  const resolvedFollowUps = followUpsForEffectiveAnswerKey({
    effectiveAnswerKey,
    followUps: itemFollowUps,
  });
  const resolvedCandidate = hasEffectiveAnswerKey(effectiveAnswerKey) ? null : llmCandidate;
  const missingFields = missingFieldsForItem(
    effectivePointCorrection,
    item,
    resolvedFollowUps,
  );
  const promptText = promptTextForItem(item);
  const pointsValue = effectivePointCorrection?.effective_max_score ?? item.maxScore;
  return {
    itemId: item.itemId,
    itemType: item.itemType,
    sequence: item.sequence,
    sourceItemFingerprint,
    title: item.title || promptText,
    typeLabel: typeLabelForItemType(item.itemType),
    pointsValue,
    pointsLabel: pointsValue === null ? "—" : `${pointsValue.toLocaleString("sv-SE")} p`,
    promptText,
    missingFields,
    status: isAttentionRow({ followUps: resolvedFollowUps, item, missingFields })
      ? "attention"
      : "complete",
    statusSymbol: statusSymbolForItem({
      candidate: resolvedCandidate,
      effectiveAnswerKey,
      item,
      missingFields,
    }),
    answerKeyReviewOrigin: null,
    answerKeyReviewReasons: [],
    answerKeyReviewState: null,
    answerKeyReviewStateLabel: statusSymbolForItem({
      candidate: resolvedCandidate,
      effectiveAnswerKey,
      item,
      missingFields,
    }) === "ai_suggestion"
      ? "Granska"
      : missingFields.includes("Facit") && isAnswerKeyReviewableItemType(item.itemType)
        ? "Kontrollera"
        : "Klart",
    answerKeyReviewStateReasonLabel:
      missingFields.includes("Facit") && isAnswerKeyReviewableItemType(item.itemType)
        ? "Saknar facitsvar"
        : null,
    currentAnswerKeyProvenance: hasEffectiveAnswerKey(effectiveAnswerKey)
      ? effectiveAnswerKey.provenance
      : item.answerKey.provenance,
    effectiveAnswerKey,
    effectivePointCorrection,
    llmCandidate: resolvedCandidate,
    manualFollowUpMessages: resolvedFollowUps
      .map((followUp) => followUp.message)
      .filter((message) => message.length > 0),
    alternatives: projectAlternatives(item),
    gaps: projectGaps(item),
    lucktextStructure: projectLucktextStructure(item),
  };
}
