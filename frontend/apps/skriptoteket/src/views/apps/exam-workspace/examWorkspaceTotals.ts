/**
 * Non-blocking comparisons of the totals the exam text prints with the
 * editable question points (user ruling 2026-10-17). A difference is a
 * warning that never stops Spara or an export; the workspace derives it live.
 */
import type { NativeExamDocument, NativeExamItem } from "../../../api/examWorkspace";

/** The printed total when it differs from the sum of the questions' points, else null. */
export function examWorkspacePrintedDifference(
  printed: number | null | undefined,
  items: NativeExamItem[],
): number | null {
  if (printed == null) {
    return null;
  }
  const computed = items.reduce((sum, item) => sum + (item.points ?? 0), 0);
  // Decimal points are represented as binary floats. Ignore only accumulated
  // representation error, not a meaningful difference in the printed score.
  const tolerance = Number.EPSILON * Math.max(1, Math.abs(printed), Math.abs(computed)) *
    Math.max(1, items.length);
  return Math.abs(printed - computed) <= tolerance ? null : printed;
}

export function examWorkspaceExamPrintedDifference(document: NativeExamDocument): number | null {
  return examWorkspacePrintedDifference(document.header.printed_total, document.items);
}

/** The exam text prints no exam total any more; the questions' sum stands. */
export function withoutExamPrintedTotal(document: NativeExamDocument): NativeExamDocument {
  return { ...document, header: { ...document.header, printed_total: null } };
}

/** The exam text prints no total over this part any more. */
export function withoutPartPrintedTotal(document: NativeExamDocument, parentId: string): NativeExamDocument {
  return {
    ...document,
    parents: document.parents.map((parent) =>
      parent.parent_id === parentId ? { ...parent, printed_total: null } : parent,
    ),
  };
}

/** Clears the exam total and every part total at once. */
export function withoutPrintedTotals(document: NativeExamDocument): NativeExamDocument {
  return {
    ...withoutExamPrintedTotal(document),
    parents: document.parents.map((parent) => ({ ...parent, printed_total: null })),
  };
}

export function examWorkspaceFormatPoints(points: number): string {
  return points.toLocaleString("sv-SE", { maximumFractionDigits: 2 });
}

/**
 * The sum ("14 p") and, when the exam text prints another total, the printed
 * note ("provtexten anger 15 p"). A difference shows every decimal, so it
 * never reads as two equal numbers.
 */
export function examWorkspacePointsParts(
  points: number,
  printed: number | null,
): { sum: string; printedNote: string | null } {
  if (printed === null) {
    return { sum: `${examWorkspaceFormatPoints(points)} p`, printedNote: null };
  }
  const exact = (value: number) => value.toLocaleString("sv-SE", { maximumSignificantDigits: 15 });
  return { sum: `${exact(points)} p`, printedNote: `provtexten anger ${exact(printed)} p` };
}

/** "14 p", or "14 p · provtexten anger 15 p" when the exam text prints another total. */
export function examWorkspacePointsLine(points: number, printed: number | null): string {
  const { sum, printedNote } = examWorkspacePointsParts(points, printed);
  return printedNote === null ? sum : `${sum} · ${printedNote}`;
}
