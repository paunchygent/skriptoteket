/**
 * Exam workspace import-time points check (TASK-SKRIPT-40-04-23).
 *
 * Domain purpose:
 *   Right after an import, the question list names the questions whose
 *   points differ from the points the source printed for them, in one
 *   floating line with "Visa frågorna" stepping through them and "Avfärda"
 *   hiding the line and every mark. A question whose own lines printed two
 *   different values counts as differing too (TASK-SKRIPT-40-04-23 P8).
 *   Nothing is stored: the open-workspace state lives in
 *   `useExamWorkspaceImportPoints`.
 *
 * Relationships:
 *   - Pure; the difference rule is `examWorkspaceSourcePointsDiffer` in
 *     `examWorkspaceTotals`, shared with the printed-total lines, plus the
 *     two-value rule `examWorkspaceSourcePointsConflict` used only here.
 *   - `ExamWorkspaceView` provides the marked ids under
 *     `EXAM_WORKSPACE_IMPORT_POINTS_KEY` for the Poäng field's hint, and
 *     passes them to `ExamWorkspaceQuestionList` for the line and row marks.
 */

import type { InjectionKey, Ref } from "vue";

import type { NativeExamItem } from "../../../api/examWorkspace";
import {
  examWorkspaceFormatExactPoints,
  examWorkspaceSourcePointsConflict,
  examWorkspaceSourcePointsDiffer,
} from "./examWorkspaceTotals";

/** The marked question ids while the import line shows; empty otherwise. */
export const EXAM_WORKSPACE_IMPORT_POINTS_KEY: InjectionKey<Readonly<Ref<ReadonlySet<string>>>> =
  Symbol("exam-workspace-import-points");

/** The differing questions in the order of `listOrder` (the list's item ids). */
export function examWorkspaceImportPointsItemIds(listOrder: string[], items: NativeExamItem[]): string[] {
  const itemById = new Map(items.map((item) => [item.item_id, item]));
  return listOrder.filter((id) => {
    const item = itemById.get(id);
    return (
      item !== undefined &&
      (examWorkspaceSourcePointsDiffer(item) || examWorkspaceSourcePointsConflict(item))
    );
  });
}

/**
 * The Poäng field's import-time hint for one question: with conflicting
 * printed values, "Provtexten: " followed by each value with " p", joined
 * with ", " and the last with " och "; else the single printed value's
 * "Provtexten: {n} p"; else null.
 */
export function examWorkspaceSourcePointsHintText(item: NativeExamItem): string | null {
  const conflicting = item.conflicting_source_points;
  if (conflicting.length > 1) {
    const parts = conflicting.map((value) => `${examWorkspaceFormatExactPoints(value)} p`);
    return `Provtexten: ${parts.slice(0, -1).join(", ")} och ${parts[parts.length - 1]}`;
  }
  const source = item.source_points ?? null;
  if (source === null) {
    return null;
  }
  return `Provtexten: ${examWorkspaceFormatExactPoints(source)} p`;
}

/** The next differing question after the selected one, wrapping to the first; null with none. */
export function examWorkspaceNextImportPointsTarget(ids: string[], selectedId: string | null): string | null {
  if (ids.length === 0) {
    return null;
  }
  const at = selectedId === null ? -1 : ids.indexOf(selectedId);
  return ids[(at + 1) % ids.length] ?? null;
}

/** The import line's sentence for `count` differing questions. */
export function examWorkspaceImportPointsText(count: number): string {
  return count === 1 ? "1 fråga avviker från provtexten" : `${count} frågor avviker från provtexten`;
}
