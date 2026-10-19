/**
 * Exam workspace footer note lines.
 *
 * Domain purpose:
 *   One neutral footer line per printed total that differs from its
 *   questions' sum: the exam line first, then one line per differing part in
 *   document order. The list is a discriminated union on `kind` so a second
 *   line kind slots in without touching the printed-total member.
 *
 * Relationships:
 *   - Pure; consumed by `ExamWorkspaceQuestionList`, which maps each line to
 *     its glyph-only actions.
 *   - Reads the mismatches from `examWorkspaceTotals` with the list's part
 *     numbers; never recomputes a difference.
 */

import type { ExamWorkspaceListEntry } from "./examWorkspaceListEntries";
import { examWorkspaceFormatExactPoints } from "./examWorkspaceTotals";
import type { PrintedTotalMismatch } from "./examWorkspaceTotals";

/** One printed-total footer line: the text with its jump target and the level it clears. */
export type PrintedTotalNoteLine = {
  kind: "printed-total";
  key: string;
  text: string;
  parentId: string | null;
  target: string | null;
  sum: number;
};

/** One footer note line; a second kind joins this union without touching the printed-total member. */
export type ExamWorkspaceNoteLine = PrintedTotalNoteLine;

/**
 * The footer lines in order, named with the list's part numbers; a part the
 * list never names, or names with no number, is skipped.
 */
export function buildExamWorkspaceNoteLines(
  mismatches: PrintedTotalMismatch[],
  entries: ExamWorkspaceListEntry[],
): ExamWorkspaceNoteLine[] {
  const entryById = new Map(entries.map((entry) => [entry.id, entry]));
  const rendered: ExamWorkspaceNoteLine[] = [];
  for (const mismatch of mismatches) {
    if (mismatch.level === "exam") {
      rendered.push({
        key: "exam",
        kind: "printed-total",
        parentId: null,
        sum: mismatch.sum,
        target: mismatch.target,
        text: `Provtexten säger ${examWorkspaceFormatExactPoints(mismatch.printed)} p, frågorna ger ${examWorkspaceFormatExactPoints(mismatch.sum)} p.`,
      });
      continue;
    }
    const entry = entryById.get(mismatch.parentId);
    if (!entry || entry.kind !== "parent" || entry.label === "") {
      continue;
    }
    rendered.push({
      key: `part-${mismatch.parentId}`,
      kind: "printed-total",
      parentId: mismatch.parentId,
      sum: mismatch.sum,
      target: mismatch.target,
      text: `Del ${entry.label} i provtexten säger ${examWorkspaceFormatExactPoints(mismatch.printed)} p, frågorna ger ${examWorkspaceFormatExactPoints(mismatch.sum)} p.`,
    });
  }
  return rendered;
}
