/**
 * Exam workspace export blockers.
 *
 * Domain purpose:
 *   What stops the export, one row per question in the list's own words
 *   ("Fråga 3: facit saknas"), shown before the teacher clicks a format
 *   (user rule 2026-10-17). Each row names the first problem, the field
 *   that holds it, and the one-click fix where the workspace can make it:
 *   Markera som granskad for an unbuilt question, Godkänn for an AI key
 *   nobody approved, Föreslå facit for a missing key, Ta bort tomma for
 *   empty options nobody keyed, and Ta bort rubrikformat for a heading in a
 *   dropdown option. The fixes are pure item transitions. A title with no
 *   letter or digit adds one row of its own ahead of the questions that
 *   jumps to the title field; the teacher fixes it by typing.
 *
 * Relationships:
 *   - Reads readiness from `examWorkspaceItemReadiness` and the list labels
 *     from `examWorkspaceListEntries`; the server's refusal adds its reasons.
 *   - Consumed by `ExamWorkspaceView` and the export menu and drawer.
 */

import type { NativeExamItem } from "../../../api/examWorkspace";
import { examWorkspaceTitleWithoutText } from "./examWorkspaceItemReadiness";
import type { ExamWorkspaceReadinessReason } from "./examWorkspaceItemReadiness";
import { examWorkspaceShortProblem } from "./examWorkspaceListEntries";
import type { ExamWorkspaceListEntry } from "./examWorkspaceListEntries";
import { bodyText } from "./examWorkspaceRichText";
import { EXAM_WORKSPACE_EXPORT_BLOCKER_COPY } from "./useExamWorkspaceExports";

export type ExamWorkspaceBlockerFix = "review" | "approve" | "suggest_key" | "remove_empty" | "strip_headings";

export type ExamWorkspaceBlockerEntry = {
  /** The question; null for the exam's title. */
  itemId: string | null;
  label: string | null;
  reason: ExamWorkspaceReadinessReason | "title_without_text";
  /** The problem in the list's words: "facit saknas". */
  problem: string;
  fix: ExamWorkspaceBlockerFix | null;
  /** The field that holds the problem; a gap chip opens its popover. */
  focus: string | null;
};

export const EXAM_WORKSPACE_BLOCKER_FIX_LABELS: Record<ExamWorkspaceBlockerFix, string> = {
  approve: "Godkänn",
  remove_empty: "Ta bort tomma",
  review: "Markera som granskad",
  strip_headings: "Ta bort rubrikformat",
  suggest_key: "Föreslå facit",
};

const CONVERTING_PROBLEM = "konverteras fortfarande";

function isEmpty(body: NativeExamItem["choices"][number]["body"]): boolean {
  return bodyText(body).length === 0;
}

/** The choices and dropdown options a removal keeps: each list keeps two filled entries and its key. */
function removableEmpties(item: NativeExamItem): boolean {
  const keyedChoices = new Set(item.answer_key.correct_choice_ids ?? []);
  const emptyChoices = item.choices.filter((choice) => isEmpty(choice.body));
  if (emptyChoices.length > 0) {
    if (emptyChoices.some((choice) => keyedChoices.has(choice.choice_id))) return false;
    if (item.choices.length - emptyChoices.length < 2) return false;
  }
  return item.gaps.every((gap) => {
    const empty = gap.options.filter((option) => isEmpty(option.body));
    if (empty.length === 0) return true;
    return (
      !empty.some((option) => option.choice_id === gap.correct_option_id) &&
      gap.options.length - empty.length >= 2
    );
  });
}

/** Drop every empty choice and dropdown option; offered only when `removableEmpties` holds. */
export function withoutEmptyOptions(item: NativeExamItem): NativeExamItem {
  return {
    ...item,
    choices: item.choices.filter((choice) => !isEmpty(choice.body)),
    gaps: item.gaps.map((gap) => ({ ...gap, options: gap.options.filter((option) => !isEmpty(option.body)) })),
  };
}

/** Make every dropdown option's paragraphs plain text. */
export function withoutOptionHeadings(item: NativeExamItem): NativeExamItem {
  return {
    ...item,
    gaps: item.gaps.map((gap) => ({
      ...gap,
      options: gap.options.map((option) => ({
        ...option,
        body: option.body.map((paragraph) => ({ ...paragraph, heading_level: null })),
      })),
    })),
  };
}

function blockerFix(item: NativeExamItem, reason: ExamWorkspaceReadinessReason): ExamWorkspaceBlockerFix | null {
  switch (reason) {
    case "unbuilt_question":
      return "review";
    case "machine_proposed_key_unreviewed":
      return "approve";
    case "missing_answer_key":
      return "suggest_key";
    case "empty_choice":
    case "empty_gap_option":
      return removableEmpties(item) ? "remove_empty" : null;
    case "inline_choice_option_heading":
      return "strip_headings";
    default:
      return null;
  }
}

const testId = (id: string) => `[data-test="${id}"]`;
const POINTS = testId("exam-workspace-item-points-input");

function gapChip(gapId: string | undefined): string | null {
  return gapId ? `[data-gap-id="${gapId}"]` : null;
}

function choiceText(choiceId: string | undefined): string | null {
  return choiceId ? `[data-test^="exam-workspace-choice-text-${choiceId}"]` : null;
}

function keyFocus(item: NativeExamItem): string | null {
  if (item.kind === "single_choice" || item.kind === "multiple_response") {
    const first = item.choices[0]?.choice_id;
    return first ? testId(`exam-workspace-choice-correct-${first}`) : null;
  }
  if (item.kind === "matching") return '[data-test^="exam-workspace-match-tick-"]';
  return gapChip(item.gaps[0]?.gap_id);
}

function blockerFocus(item: NativeExamItem, reason: ExamWorkspaceReadinessReason): string | null {
  switch (reason) {
    case "unbuilt_question":
    case "machine_proposed_key_unreviewed":
      return testId("exam-workspace-review");
    case "missing_answer_key":
      return keyFocus(item);
    case "partial_gap_key":
      return gapChip(
        item.gaps.find((gap) => gap.accepted_values.length === 0 && gap.correct_option_id === null)?.gap_id,
      );
    case "incomplete_match_key": {
      const unticked = item.match_left.find(
        (left) => !item.answer_key.match_pairs.some((pair) => pair.left_id === left.left_id),
      );
      return unticked ? `[data-test^="exam-workspace-match-tick-${unticked.left_id}-"]` : null;
    }
    case "missing_points":
    case "negative_points":
    case "criteria_points_mismatch":
      return POINTS;
    case "empty_choice":
      return choiceText(item.choices.find((choice) => isEmpty(choice.body))?.choice_id);
    case "empty_gap_option":
      return gapChip(item.gaps.find((gap) => gap.options.some((option) => isEmpty(option.body)))?.gap_id);
    case "inline_choice_option_heading":
      return gapChip(
        item.gaps.find((gap) => gap.options.some((option) => option.body.some((p) => p.heading_level !== null)))
          ?.gap_id,
      );
    case "empty_match_entry": {
      const left = item.match_left.find((entry) => isEmpty(entry.body));
      if (left) return `[data-test^="exam-workspace-match-left-text-${left.left_id}"]`;
      const right = item.match_right.find((entry) => isEmpty(entry.body));
      return right ? `[data-test^="exam-workspace-match-right-text-${right.right_id}"]` : null;
    }
    case "empty_criterion_text": {
      const index = item.criteria.findIndex((criterion) => criterion.text.trim().length === 0);
      return index >= 0 ? testId(`exam-workspace-criterion-text-${index}`) : null;
    }
    case "invalid_criterion_points":
      return '[data-test^="exam-workspace-criterion-points-"]';
    case "criteria_on_wrong_kind":
      return testId("exam-workspace-criteria");
  }
}

/**
 * One row per question that stops the export, in list order: the client's
 * first reason, else the first reason the server's last refusal gave.
 */
export function examWorkspaceBlockerEntries(
  entries: ExamWorkspaceListEntry[],
  items: NativeExamItem[],
  readinessByItemId: Record<string, ExamWorkspaceReadinessReason[]>,
  serverReasonsByItemId: Record<string, ExamWorkspaceReadinessReason[]>,
): ExamWorkspaceBlockerEntry[] {
  const byId = new Map(items.map((item) => [item.item_id, item]));
  return entries.flatMap((entry) => {
    const item = entry.kind === "item" ? byId.get(entry.id) : undefined;
    const reason = (readinessByItemId[entry.id] ?? [])[0] ?? (serverReasonsByItemId[entry.id] ?? [])[0];
    if (!item || entry.kind !== "item" || reason === undefined) {
      return [];
    }
    const converting = entry.status === "converting";
    return [{
      fix: converting ? null : blockerFix(item, reason),
      focus: converting ? null : blockerFocus(item, reason),
      itemId: item.item_id,
      label: entry.label,
      problem: converting ? CONVERTING_PROBLEM : examWorkspaceShortProblem(reason),
      reason,
    }];
  });
}

/** The field that holds the exam title: Provets uppgifter, which the jump opens first. */
export const EXAM_WORKSPACE_TITLE_FIELD = testId("exam-workspace-metadata-title");

/**
 * The row for an exam title with no letter or digit, ahead of the question
 * rows: the client's own check, else the server's last refusal of this title.
 * The row names the one fix in the copy; the jump opens the title field.
 */
export function examWorkspaceTitleBlockerEntries(
  title: string,
  serverRefusedTitle: boolean,
): ExamWorkspaceBlockerEntry[] {
  if (!examWorkspaceTitleWithoutText(title) && !serverRefusedTitle) {
    return [];
  }
  return [{
    fix: null,
    focus: EXAM_WORKSPACE_TITLE_FIELD,
    itemId: null,
    label: null,
    problem: EXAM_WORKSPACE_EXPORT_BLOCKER_COPY.title_without_text.replace(/\.$/, ""),
    reason: "title_without_text",
  }];
}
