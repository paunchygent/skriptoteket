/**
 * Exam workspace footer note lines.
 *
 * Domain purpose:
 *   One neutral footer line per printed total that differs from its
 *   questions' sum: the exam line first, then one line per differing part in
 *   document order. Right after an import, one more line names the questions
 *   whose points differ from the source: it comes first, above the
 *   printed-total lines. The list is a discriminated union on `kind` so
 *   further line kinds slot in without touching the existing members.
 *
 * Relationships:
 *   - Pure; consumed by `ExamWorkspaceQuestionList`, which maps each line to
 *     its glyph-only actions.
 *   - Reads the mismatches from `examWorkspaceTotals` with the list's part
 *     numbers; never recomputes a difference.
 *   - Reads the import sentence from `examWorkspaceImportPoints`; never
 *     recomputes the import difference.
 */

import type { ExamWorkspaceListEntry } from "./examWorkspaceListEntries";
import { examWorkspaceImportPointsText } from "./examWorkspaceImportPoints";
import { examWorkspaceFormatExactPoints } from "./examWorkspaceTotals";
import type { PrintedTotalMismatch } from "./examWorkspaceTotals";

/** One import-time line: the sentence with the differing questions' ids in list order. */
export type ImportPointsNoteLine = {
  kind: "import-points";
  key: "import-points";
  text: string;
  itemIds: string[];
};

/** One printed-total footer line: the text with its jump target and the level it clears. */
export type PrintedTotalNoteLine = {
  kind: "printed-total";
  key: string;
  text: string;
  parentId: string | null;
  target: string | null;
  sum: number;
};

/** One footer note line: the import-points line joins without touching the printed-total member. */
export type ExamWorkspaceNoteLine = ImportPointsNoteLine | PrintedTotalNoteLine;

/**
 * The footer lines in order: the import line first when any question
 * differs, then the exam line, then part lines; a part the
 * list never names, or names with no number, is skipped.
 */
export function buildExamWorkspaceNoteLines(
  mismatches: PrintedTotalMismatch[],
  entries: ExamWorkspaceListEntry[],
  importPointsIds: string[],
): ExamWorkspaceNoteLine[] {
  const entryById = new Map(entries.map((entry) => [entry.id, entry]));
  const rendered: ExamWorkspaceNoteLine[] = [];
  if (importPointsIds.length > 0) {
    rendered.push({
      key: "import-points",
      kind: "import-points",
      text: examWorkspaceImportPointsText(importPointsIds.length),
      itemIds: [...importPointsIds],
    });
  }
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
