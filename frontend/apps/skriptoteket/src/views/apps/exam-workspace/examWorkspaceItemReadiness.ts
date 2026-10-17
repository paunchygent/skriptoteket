/**
 * Exam workspace per-item export readiness.
 *
 * Domain purpose:
 *   Tell the teacher, while editing, which questions would stop a QTI, PDF,
 *   or DOCX export, so invalid states are explained at the question instead
 *   of discovered at export. The server export gate stays authoritative;
 *   this mirrors its reasons, including the unbuilt question (an item
 *   printed from source that the teacher has not marked reviewed; a
 *   converted item that needs review does not block), and adds the item
 *   states the save refuses:
 *   a partial gap key, an incomplete matching key, points that are not
 *   greater than zero, a choice or matching entry without text, and
 *   free-text criteria that lack text, carry invalid points, are not the
 *   item's points, or sit on a non-free-text item.
 *
 * Relationships:
 *   - Mirrors `native_export_blockers` in
 *     `domain/curated_apps/exam_workspace/native_exam_document.py`.
 *   - Reads the save rules from `examWorkspaceItemSaveRules` and
 *     `examWorkspaceAnswerKeyRules`.
 *   - Consumed by `ExamWorkspaceView`, the question list, and the Filer
 *     readiness summary; reuses the export blocker copy.
 */

import type {
  ExamWorkspaceExportBlockerReason,
  NativeExamItem,
  NativeExamItemKind,
} from "../../../api/examWorkspace";
import {
  INCOMPLETE_MATCH_KEY_GUIDANCE,
  isIncompleteMatchingItem,
  isPartiallyKeyedGapItem,
  PARTIAL_GAP_KEY_GUIDANCE,
} from "./examWorkspaceAnswerKeyRules";
import {
  CRITERIA_ON_WRONG_KIND_GUIDANCE,
  CRITERIA_POINTS_MISMATCH_GUIDANCE,
  EMPTY_CHOICE_TEXT_GUIDANCE,
  EMPTY_CRITERION_TEXT_GUIDANCE,
  EMPTY_MATCH_TEXT_GUIDANCE,
  hasCriteriaOnWrongKind,
  hasCriteriaPointsMismatch,
  hasEmptyChoiceText,
  hasEmptyCriterionText,
  hasEmptyMatchText,
  hasInvalidCriterionPoints,
  hasNegativePoints,
  INVALID_CRITERION_POINTS_GUIDANCE,
  NEGATIVE_POINTS_GUIDANCE,
} from "./examWorkspaceItemSaveRules";
import { bodyText } from "./examWorkspaceRichText";
import { EXAM_WORKSPACE_EXPORT_BLOCKER_COPY } from "./useExamWorkspaceExports";

const KEYED_KINDS = new Set<NativeExamItemKind>([
  "gap_fill",
  "matching",
  "multiple_response",
  "single_choice",
]);

export type ExamWorkspaceReadinessReason =
  | ExamWorkspaceExportBlockerReason
  | "criteria_on_wrong_kind"
  | "criteria_points_mismatch"
  | "empty_choice_text"
  | "empty_criterion_text"
  | "empty_match_text"
  | "incomplete_match_key"
  | "invalid_criterion_points"
  | "negative_points"
  | "partial_gap_key";

const READINESS_COPY: Record<ExamWorkspaceReadinessReason, string> = {
  ...EXAM_WORKSPACE_EXPORT_BLOCKER_COPY,
  criteria_on_wrong_kind: CRITERIA_ON_WRONG_KIND_GUIDANCE,
  criteria_points_mismatch: CRITERIA_POINTS_MISMATCH_GUIDANCE,
  empty_choice_text: EMPTY_CHOICE_TEXT_GUIDANCE,
  empty_criterion_text: EMPTY_CRITERION_TEXT_GUIDANCE,
  empty_match_text: EMPTY_MATCH_TEXT_GUIDANCE,
  incomplete_match_key: INCOMPLETE_MATCH_KEY_GUIDANCE,
  invalid_criterion_points: INVALID_CRITERION_POINTS_GUIDANCE,
  negative_points: NEGATIVE_POINTS_GUIDANCE,
  partial_gap_key: PARTIAL_GAP_KEY_GUIDANCE,
};

export function examWorkspaceItemReadiness(item: NativeExamItem): ExamWorkspaceReadinessReason[] {
  const reasons: ExamWorkspaceReadinessReason[] = [];
  const source = item.retry_source;
  const missingPicture = source
    ? [...source.chunks, ...source.key_chunks, ...source.context_chunks].some(
      (chunk) => chunk.missing_images.length > 0,
    )
    : false;
  if (
    item.review.state === "review_required" &&
    (item.review.parse_origin === "deterministic" || missingPicture)
  ) {
    reasons.push("unbuilt_question");
  }
  if (item.answer_key.origin === "machine_proposed") {
    reasons.push("machine_proposed_key_unreviewed");
  }
  if (KEYED_KINDS.has(item.kind) && item.answer_key.origin === "absent") {
    reasons.push("missing_answer_key");
  }
  if (isPartiallyKeyedGapItem(item)) {
    reasons.push("partial_gap_key");
  }
  if (isIncompleteMatchingItem(item)) {
    reasons.push("incomplete_match_key");
  }
  if (item.points === null) {
    reasons.push("missing_points");
  }
  if (hasNegativePoints(item)) {
    reasons.push("negative_points");
  }
  if (hasEmptyChoiceText(item)) {
    reasons.push("empty_choice_text");
  }
  if (item.gaps.some((gap) => gap.options.some((option) => bodyText(option.body) === ""))) {
    reasons.push("empty_gap_option");
  }
  if (hasEmptyMatchText(item)) {
    reasons.push("empty_match_text");
  }
  if (hasEmptyCriterionText(item)) {
    reasons.push("empty_criterion_text");
  }
  if (hasInvalidCriterionPoints(item)) {
    reasons.push("invalid_criterion_points");
  }
  if (hasCriteriaPointsMismatch(item)) {
    reasons.push("criteria_points_mismatch");
  }
  if (hasCriteriaOnWrongKind(item)) {
    reasons.push("criteria_on_wrong_kind");
  }
  return reasons;
}

export function examWorkspaceReadinessCopy(reason: ExamWorkspaceReadinessReason): string {
  return READINESS_COPY[reason];
}

/** Swedish readiness copy per item id, only for items that would stop an export. */
export function examWorkspaceReadinessByItemId(
  items: NativeExamItem[],
): Record<string, string[]> {
  const byItemId: Record<string, string[]> = {};
  for (const item of items) {
    const reasons = examWorkspaceItemReadiness(item);
    if (reasons.length > 0) {
      byItemId[item.item_id] = reasons.map(examWorkspaceReadinessCopy);
    }
  }
  return byItemId;
}
