/**
 * Non-blocking comparisons of source-printed totals with editable item points.
 * The workspace derives these signals live; they never affect export readiness.
 */
import type { NativeExamDocument, NativeExamItem } from "../../../api/examWorkspace";

/** Compare a printed total with the sum of the items that have points. */
export function examWorkspaceTotalSignal(
  printed: number | null | undefined,
  items: NativeExamItem[],
  scope: "exam" | "parent" = "exam",
): string | null {
  if (printed == null) {
    return null;
  }
  const computed = items.reduce((sum, item) => sum + (item.points ?? 0), 0);
  // Decimal points are represented as binary floats. Ignore only accumulated
  // representation error, not a meaningful difference in the printed score.
  const tolerance = Number.EPSILON * Math.max(1, Math.abs(printed), Math.abs(computed)) *
    Math.max(1, items.length);
  if (Math.abs(printed - computed) <= tolerance) {
    return null;
  }
  const format = (points: number) => points.toLocaleString("sv-SE", { maximumSignificantDigits: 15 });
  const label = scope === "exam" ? "Tryckt totalsumma" : "Tryckt delsumma";
  return `${label} ${format(printed)} p, frågorna ger ${format(computed)} p`;
}

export function examWorkspaceExamTotalSignal(document: NativeExamDocument): string | null {
  return examWorkspaceTotalSignal(document.header.printed_total, document.items);
}
