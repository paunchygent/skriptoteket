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

import type { DigiExamItemType } from "../../../api/sirConvertGateway";
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

export type ExamConverterMissingFieldLabel = "Facit" | "Poäng";
export type ExamConverterQuestionReviewStatus = "complete" | "attention";

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

export type ExamConverterQuestionReviewRow = {
  itemId: string;
  itemType: DigiExamItemType;
  sequence: number;
  sourceItemFingerprint: string | null;
  title: string;
  typeLabel: string;
  pointsLabel: string;
  promptText: string;
  missingFields: ExamConverterMissingFieldLabel[];
  status: ExamConverterQuestionReviewStatus;
  manualFollowUpMessages: string[];
  alternatives: ExamConverterQuestionAlternative[];
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
  gaps: Record<string, unknown>[];
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
      return "Flerval: ett val";
    case DIGIEXAM_ITEM_TYPE_MULTIPLE_RESPONSE:
      return "Flerval: flera val";
    case DIGIEXAM_ITEM_TYPE_OPEN_ENDED:
      return "Fritext";
    default:
      return "Okänd";
  }
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
  item: DigiExamIrItem,
  followUps: DigiExamIrManualFollowUp[],
): ExamConverterMissingFieldLabel[] {
  const labels: ExamConverterMissingFieldLabel[] = [];
  if (item.maxScore === null) {
    labels.push("Poäng");
  }
  if (
    followUps.some(
      (followUp) => followUp.reason === DIGIEXAM_MANUAL_FOLLOW_UP_MANUAL_ANSWER_KEY_REQUIRED,
    )
  ) {
    labels.push("Facit");
  }
  return uniqueLabels(labels);
}

function isActionableFollowUp(followUp: DigiExamIrManualFollowUp): boolean {
  return (
    followUp.reason === DIGIEXAM_MANUAL_FOLLOW_UP_MANUAL_ANSWER_KEY_REQUIRED ||
    followUp.reason === DIGIEXAM_MANUAL_FOLLOW_UP_UNSUPPORTED_ITEM_TYPE ||
    followUp.reason === DIGIEXAM_MANUAL_FOLLOW_UP_PARSER_WARNING_BLOCKS_RENDERING
  );
}

function isAttentionRow(params: {
  followUps: DigiExamIrManualFollowUp[];
  item: DigiExamIrItem;
  missingFields: ExamConverterMissingFieldLabel[];
}): boolean {
  return (
    params.missingFields.length > 0 ||
    params.followUps.some(isActionableFollowUp) ||
    params.item.warnings.length > 0
  );
}

export function projectQuestionReviewRow(
  item: DigiExamIrItem,
  itemFollowUps: DigiExamIrManualFollowUp[],
  sourceItemFingerprint: string | null,
): ExamConverterQuestionReviewRow {
  const missingFields = missingFieldsForItem(item, itemFollowUps);
  const promptText = promptTextForItem(item);
  return {
    itemId: item.itemId,
    itemType: item.itemType,
    sequence: item.sequence,
    sourceItemFingerprint,
    title: item.title || promptText,
    typeLabel: typeLabelForItemType(item.itemType),
    pointsLabel: item.maxScore === null ? "—" : `${item.maxScore.toLocaleString("sv-SE")} p`,
    promptText,
    missingFields,
    status: isAttentionRow({ followUps: itemFollowUps, item, missingFields })
      ? "attention"
      : "complete",
    manualFollowUpMessages: itemFollowUps
      .map((followUp) => followUp.message)
      .filter((message) => message.length > 0),
    alternatives: projectAlternatives(item),
    lucktextStructure: projectLucktextStructure(item),
  };
}
