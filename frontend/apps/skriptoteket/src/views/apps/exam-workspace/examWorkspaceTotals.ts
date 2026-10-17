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

export function examWorkspaceFormatPoints(points: number): string {
  return points.toLocaleString("sv-SE", { maximumFractionDigits: 2 });
}

/**
 * "14 p", or "14 p · provtexten anger 15 p" when the exam text prints another
 * total. A difference shows every decimal, so it never reads as two equal numbers.
 */
export function examWorkspacePointsLine(points: number, printed: number | null): string {
  if (printed === null) {
    return `${examWorkspaceFormatPoints(points)} p`;
  }
  const exact = (value: number) => value.toLocaleString("sv-SE", { maximumSignificantDigits: 15 });
  return `${exact(points)} p · provtexten anger ${exact(printed)} p`;
}
