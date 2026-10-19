/**
 * Exam workspace per-item export readiness.
 *
 * Domain purpose:
 *   Tell the teacher, while editing, which questions would stop a QTI, PDF,
 *   or DOCX export, so invalid states are explained at the question instead
 *   of discovered at export. The server export gate stays authoritative;
 *   this mirrors its reasons, including the unbuilt question (an explicit
 *   source fallback or an item missing a picture that the teacher has not
 *   marked reviewed; a converted item that needs review does not block),
 *   dropdown option headings, a dropdown with fewer than two options, and
 *   choices, gap options or matching entries without non-whitespace text (an
 *   ordering question names its blank steps "empty_ordering_step" and needs at
 *   least two steps, otherwise "ordering_too_few_steps"). Save validity remains
 *   separate. Readiness
 *   also adds the item states the save refuses:
 *   a partial gap key, an incomplete matching key, invalid points, and
 *   free-text criteria that lack text, carry invalid points, are not the
 *   item's points, or sit on a non-free-text item.
 *
 * Relationships:
 *   - Mirrors the per-item rules of `native_export_blockers` in
 *     `domain/curated_apps/exam_workspace/native_exam_export_rules.py`.
 *   - Reads the save rules from `examWorkspaceItemSaveRules` and
 *     `examWorkspaceAnswerKeyRules`.
 *   - Consumed by `ExamWorkspaceView`, the question list, and the Filer
 *     readiness summary; reuses the export blocker copy.
 */

import type {
  NativeExamGap,
  NativeExamItem,
  NativeExamItemKind,
} from "../../../api/examWorkspace";
import type {
  ExamWorkspaceExportChecklistResponse,
  ExamWorkspaceItemExportBlockerReason,
} from "../../../api/examWorkspaceExports";
import {
  dropdownGapsWithoutCorrectOption,
  GAP_WITHOUT_CORRECT_OPTION_GUIDANCE,
  INCOMPLETE_MATCH_KEY_GUIDANCE,
  isIncompleteMatchingItem,
  isPartiallyKeyedGapItem,
  PARTIAL_GAP_KEY_GUIDANCE,
} from "./examWorkspaceAnswerKeyRules";
import {
  CRITERIA_ON_WRONG_KIND_GUIDANCE,
  CRITERIA_POINTS_MISMATCH_GUIDANCE,
  EMPTY_CRITERION_TEXT_GUIDANCE,
  hasCriteriaOnWrongKind,
  hasCriteriaPointsMismatch,
  hasEmptyCriterionText,
  hasInvalidCriterionPoints,
  hasNegativePoints,
  INVALID_CRITERION_POINTS_GUIDANCE,
  NEGATIVE_POINTS_GUIDANCE,
} from "./examWorkspaceItemSaveRules";
import { bodyText } from "./examWorkspaceRichText";
import { isEmptyBody } from "./examWorkspaceRichTextDocument";
import { EXAM_WORKSPACE_EXPORT_BLOCKER_COPY } from "./useExamWorkspaceExports";

const KEYED_KINDS = new Set<NativeExamItemKind>([
  "gap_fill",
  "inline_choice",
  "matching",
  "multiple_response",
  "ordering",
  "single_choice",
]);

const GAP_KINDS = new Set<NativeExamItemKind>(["gap_fill", "inline_choice"]);

// The server's export rule owns this minimum and publishes it on the export
// checklist contract; a changed server value fails this typecheck.
const INLINE_CHOICE_MIN_OPTIONS =
  2 satisfies ExamWorkspaceExportChecklistResponse["inline_choice_min_options"];

/** Dropdown gaps with fewer options than the export allows (D3). */
export function dropdownGapsWithTooFewOptions(item: NativeExamItem): NativeExamGap[] {
  return item.kind === "inline_choice"
    ? item.gaps.filter((gap) => gap.options.length < INLINE_CHOICE_MIN_OPTIONS)
    : [];
}

export type ExamWorkspaceReadinessReason =
  | ExamWorkspaceItemExportBlockerReason
  | "criteria_on_wrong_kind"
  | "criteria_points_mismatch"
  | "empty_criterion_text"
  | "gap_without_correct_option"
  | "incomplete_match_key"
  | "invalid_criterion_points"
  | "negative_points"
  | "partial_gap_key";

const READINESS_COPY: Record<ExamWorkspaceReadinessReason, string> = {
  ...EXAM_WORKSPACE_EXPORT_BLOCKER_COPY,
  criteria_on_wrong_kind: CRITERIA_ON_WRONG_KIND_GUIDANCE,
  criteria_points_mismatch: CRITERIA_POINTS_MISMATCH_GUIDANCE,
  empty_criterion_text: EMPTY_CRITERION_TEXT_GUIDANCE,
  gap_without_correct_option: GAP_WITHOUT_CORRECT_OPTION_GUIDANCE,
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
    (item.review.parse_origin === "source_fallback" || missingPicture)
  ) {
    reasons.push("unbuilt_question");
  }
  if (isEmptyBody(item.body)) {
    reasons.push("empty_question_text");
  }
  if (GAP_KINDS.has(item.kind) && item.gaps.length === 0) {
    reasons.push("no_gaps");
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
  // An absent key already reports missing_answer_key; a claimed key needs every gap keyed.
  if (item.answer_key.origin !== "absent" && dropdownGapsWithoutCorrectOption(item).length > 0) {
    reasons.push("gap_without_correct_option");
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
  // Export needs non-whitespace text; save validity deliberately remains separate.
  if (item.kind === "ordering" && item.choices.length < 2) {
    reasons.push("ordering_too_few_steps");
  }
  if (item.choices.some((choice) => bodyText(choice.body).length === 0)) {
    reasons.push(item.kind === "ordering" ? "empty_ordering_step" : "empty_choice");
  }
  if (item.gaps.some((gap) => gap.options.some((option) => bodyText(option.body).length === 0))) {
    reasons.push("empty_gap_option");
  }
  if (
    [...item.match_left, ...item.match_right].some((entry) => bodyText(entry.body).length === 0)
  ) {
    reasons.push("empty_match_entry");
  }
  if (
    item.kind === "inline_choice" &&
    item.gaps.some((gap) => gap.options.some((option) =>
      option.body.some((paragraph) => paragraph.heading_level !== null),
    ))
  ) {
    reasons.push("inline_choice_option_heading");
  }
  if (dropdownGapsWithTooFewOptions(item).length > 0) {
    reasons.push("too_few_gap_options");
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
