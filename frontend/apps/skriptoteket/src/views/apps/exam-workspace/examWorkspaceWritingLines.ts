/**
 * Writing-line bounds and transitions for a free-text question's printed
 * writing area (W4).
 *
 * The server's one fixed house template owns these values
 * (`src/skriptoteket/domain/curated_apps/exam_conversion/exam_print_house_template.py`):
 * a free-text question starts at 8 writing lines, and the Skrivyta stepper
 * clamps a value to 1..40. The frontend mirrors them so a new question and its
 * stepper agree with the printed DOCX and PDF.
 *
 * Relationships:
 *   - `freeTextWritingLines` summarises the free-text questions for the Skrivyta
 *     field's apply-to-all popover.
 *   - The constants feed `newTeacherItem` in `examWorkspaceItemEdits`.
 *   - The transitions are applied by `useExamWorkspaceItemEdits`
 *     (`updateItemWritingLines`) and `useExamWorkspaceDocumentFields`
 *     (`applyWritingLinesToAllFreeText`).
 */

import type { NativeExamDocument, NativeExamItem } from "../../../api/examWorkspace";

export const DEFAULT_WRITING_LINES = 8;
export const MIN_WRITING_LINES = 1;
export const MAX_WRITING_LINES = 40;

/** A stepper value as a whole number of lines inside the house range. */
function clampWritingLines(lines: number): number {
  return Math.min(MAX_WRITING_LINES, Math.max(MIN_WRITING_LINES, Math.round(lines)));
}

/** Set one free-text question's writing area; every other kind is untouched. */
export function withWritingLines(item: NativeExamItem, lines: number): NativeExamItem {
  if (item.kind !== "free_text") {
    return item;
  }
  return { ...item, writing_lines: clampWritingLines(lines) };
}

/**
 * Set every free-text question's writing area to one count. A question already
 * at the count keeps its identity, and a document with nothing to change is
 * returned as it is, so the edit adds no empty undo step.
 */
export function withWritingLinesForAllFreeText(
  document: NativeExamDocument,
  lines: number,
): NativeExamDocument {
  const value = clampWritingLines(lines);
  let changed = false;
  const items = document.items.map((item) => {
    if (item.kind !== "free_text" || item.writing_lines === value) {
      return item;
    }
    changed = true;
    return { ...item, writing_lines: value };
  });
  return changed ? { ...document, items } : document;
}

/** One free-text question's display label and writing-line count (null when it carries none). */
export interface FreeTextWritingLines {
  itemId: string;
  label: string;
  lines: number | null;
}

/**
 * The document's free-text questions in document order with their display
 * labels (for example "1a") and writing-line counts.
 */
export function freeTextWritingLines(
  document: NativeExamDocument,
  labels: ReadonlyMap<string, string>,
): FreeTextWritingLines[] {
  return document.items
    .filter((item) => item.kind === "free_text")
    .map((item) => ({
      itemId: item.item_id,
      label: labels.get(item.item_id) ?? item.item_id,
      lines: item.writing_lines,
    }));
}

/** The labels of the free-text questions whose count differs from `lines`; a question with no count differs. */
export function labelsWithOtherWritingLines(freeText: readonly FreeTextWritingLines[], lines: number): string[] {
  return freeText.filter((entry) => entry.lines !== lines).map((entry) => entry.label);
}
