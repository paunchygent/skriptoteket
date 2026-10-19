/**
 * Exam workspace question list entries.
 *
 * Domain purpose:
 *   The rows of the question list in document order: a standalone question
 *   is numbered 1, 2, 3; an instruction with deluppgifter takes the next
 *   number and its deluppgifter follow as 4a, 4b. Only a unit that holds at
 *   least one question takes a number: an instruction with no questions is an
 *   unnumbered row, like Exam.net's information block. Each question row names
 *   its type and points, or the first thing that stops its export in a few
 *   words, and whether the AI wrote its key. The export menu names the same
 *   problems in the same words, numbered like the list.
 *
 * Relationships:
 *   - Pure; consumed by `ExamWorkspaceView` and the list and export menu.
 *   - Reads readiness from `examWorkspaceItemReadiness`; `examWorkspaceBlockers`
 *     reuses the short problem words.
 */

import type { NativeExamDocument, NativeExamItem } from "../../../api/examWorkspace";
import type { ExamWorkspaceReadinessReason } from "./examWorkspaceItemReadiness";
import { examWorkspacePromptExcerpt, examWorkspaceItemTypeLabel } from "./examWorkspaceRows";
import { examWorkspaceUnits } from "./examWorkspaceStructure";
import { bodyText } from "./examWorkspaceRichText";
import { examWorkspacePrintedDifference } from "./examWorkspaceTotals";

export type ExamWorkspaceItemStatus = "ok" | "warn" | "converting";

export type ExamWorkspaceItemEntry = {
  kind: "item";
  id: string;
  label: string;
  parentId: string | null;
  text: string;
  typeLabel: string;
  /** The question's kind; the UI disables grouping and moving an ordering question into a part. */
  itemKind: NativeExamItem["kind"];
  points: number | null;
  /** The first export or save problem, in a few words; null when there is none. */
  problem: string | null;
  aiKey: "interpreted" | "proposed" | null;
  status: ExamWorkspaceItemStatus;
};

export type ExamWorkspaceParentEntry = {
  kind: "parent";
  id: string;
  label: string;
  text: string;
  childIds: string[];
  points: number;
  /** The part total the exam text prints, only when it differs from `points`. */
  printedTotal: number | null;
};

export type ExamWorkspaceListEntry = ExamWorkspaceItemEntry | ExamWorkspaceParentEntry;

const SHORT_PROBLEM: Record<ExamWorkspaceReadinessReason, string> = {
  criteria_on_wrong_kind: "kriterier på fel frågetyp",
  criteria_points_mismatch: "kriterierna ger en annan summa",
  empty_choice: "tomt svarsalternativ",
  empty_criterion_text: "tomt kriterium",
  empty_question_text: "Frågetexten är tom.",
  empty_gap_option: "tomt alternativ i rullista",
  empty_match_entry: "tom rad eller kategori",
  empty_ordering_step: "tomt steg",
  incomplete_match_key: "rad utan kryss",
  inline_choice_option_heading: "rubrik i rullista",
  invalid_criterion_points: "ogiltiga kriteriepoäng",
  machine_proposed_key_unreviewed: "facit ej granskat",
  missing_answer_key: "facit saknas",
  missing_points: "poäng saknas",
  negative_points: "negativa poäng",
  no_gaps: "Frågan saknar luckor.",
  ordering_too_few_steps: "för få steg",
  partial_gap_key: "lucka utan svar",
  gap_without_correct_option: "rullista utan rätt svar",
  too_few_gap_options: "rullista med färre än två alternativ",
  unbuilt_question: "kunde inte konverteras",
};

/** The problem in a few words, as the list row and the export menu name it. */
export function examWorkspaceShortProblem(reason: ExamWorkspaceReadinessReason): string {
  return SHORT_PROBLEM[reason];
}

const LETTERS = "abcdefghijklmnopqrstuvwxyz";

function childLetter(index: number): string {
  return index < LETTERS.length ? LETTERS[index]! : `${LETTERS[Math.floor(index / LETTERS.length) - 1]}${LETTERS[index % LETTERS.length]}`;
}

function itemEntry(
  item: NativeExamItem,
  label: string,
  parentId: string | null,
  readiness: ExamWorkspaceReadinessReason[],
  converting: boolean,
): ExamWorkspaceItemEntry {
  const origin = item.answer_key.origin;
  const firstProblem = readiness[0];
  return {
    aiKey: origin === "ai_interpreted" ? "interpreted" : origin === "machine_proposed" ? "proposed" : null,
    id: item.item_id,
    itemKind: item.kind,
    kind: "item",
    label,
    parentId,
    points: item.points ?? null,
    problem: firstProblem ? SHORT_PROBLEM[firstProblem] : null,
    status: converting
      ? "converting"
      : item.review.state === "review_complete" && readiness.length === 0
        ? "ok"
        : "warn",
    text: examWorkspacePromptExcerpt(item),
    typeLabel: readiness.includes("unbuilt_question") ? "Ej konverterad" : examWorkspaceItemTypeLabel(item),
  };
}

export function examWorkspaceListEntries(
  document: NativeExamDocument,
  readinessByItemId: Record<string, ExamWorkspaceReadinessReason[]>,
  convertingItemIds: ReadonlySet<string>,
): ExamWorkspaceListEntry[] {
  const items = new Map(document.items.map((item) => [item.item_id, item]));
  const parents = new Map(document.parents.map((parent) => [parent.parent_id, parent]));
  const entries: ExamWorkspaceListEntry[] = [];
  let number = 0;
  examWorkspaceUnits(document).forEach((unit) => {
    if (unit.kind === "item") {
      number += 1;
      const item = items.get(unit.itemId)!;
      entries.push(itemEntry(item, String(number), null, readinessByItemId[item.item_id] ?? [], convertingItemIds.has(item.item_id)));
      return;
    }
    const parent = parents.get(unit.parentId)!;
    const children = unit.itemIds.flatMap((id) => (items.has(id) ? [items.get(id)!] : []));
    const text = parent.instruction.map((paragraph) => bodyText([paragraph])).join(" ").replace(/\s+/g, " ").trim();
    if (children.length === 0) {
      entries.push({
        childIds: [],
        id: parent.parent_id,
        kind: "parent",
        label: "",
        points: 0,
        printedTotal: null,
        text,
      });
      return;
    }
    number += 1;
    const partNumber = String(number);
    entries.push({
      childIds: [...unit.itemIds],
      id: parent.parent_id,
      kind: "parent",
      label: partNumber,
      points: children.reduce((sum, child) => sum + (child.points ?? 0), 0),
      printedTotal: examWorkspacePrintedDifference(parent.printed_total, children),
      text,
    });
    children.forEach((child, childIndex) => {
      entries.push(
        itemEntry(
          child,
          `${partNumber}${childLetter(childIndex)}`,
          parent.parent_id,
          readinessByItemId[child.item_id] ?? [],
          convertingItemIds.has(child.item_id),
        ),
      );
    });
  });
  return entries;
}

/** The question total; a parent's points are its deluppgifter's. */
export function examWorkspaceListTotal(entries: ExamWorkspaceListEntry[]): number {
  return entries.reduce((sum, entry) => sum + (entry.kind === "item" ? (entry.points ?? 0) : 0), 0);
}
