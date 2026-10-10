/**
 * Exam workspace per-item export readiness.
 *
 * Domain purpose:
 *   Tell the teacher, while editing, which questions would stop a QTI, PDF,
 *   or DOCX export, so invalid states are explained at the question instead
 *   of discovered at export. The server export gate stays authoritative;
 *   this mirrors its reasons and adds the item states the save refuses:
 *   a partial gap key, points that are not greater than zero, and a choice
 *   without text.
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
import { isPartiallyKeyedGapItem, PARTIAL_GAP_KEY_GUIDANCE } from "./examWorkspaceAnswerKeyRules";
import {
  EMPTY_CHOICE_TEXT_GUIDANCE,
  hasEmptyChoiceText,
  hasNonPositivePoints,
  NON_POSITIVE_POINTS_GUIDANCE,
} from "./examWorkspaceItemSaveRules";
import { EXAM_WORKSPACE_EXPORT_BLOCKER_COPY } from "./useExamWorkspaceExports";

const KEYED_KINDS = new Set<NativeExamItemKind>(["gap_fill", "multiple_response", "single_choice"]);

export type ExamWorkspaceReadinessReason =
  | ExamWorkspaceExportBlockerReason
  | "empty_choice_text"
  | "non_positive_points"
  | "partial_gap_key";

const READINESS_COPY: Record<ExamWorkspaceReadinessReason, string> = {
  ...EXAM_WORKSPACE_EXPORT_BLOCKER_COPY,
  empty_choice_text: EMPTY_CHOICE_TEXT_GUIDANCE,
  non_positive_points: NON_POSITIVE_POINTS_GUIDANCE,
  partial_gap_key: PARTIAL_GAP_KEY_GUIDANCE,
};

export function examWorkspaceItemReadiness(item: NativeExamItem): ExamWorkspaceReadinessReason[] {
  const reasons: ExamWorkspaceReadinessReason[] = [];
  if (item.review.state === "review_required") {
    reasons.push("review_required");
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
  if (item.points === null) {
    reasons.push("missing_points");
  }
  if (hasNonPositivePoints(item)) {
    reasons.push("non_positive_points");
  }
  if (hasEmptyChoiceText(item)) {
    reasons.push("empty_choice_text");
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
