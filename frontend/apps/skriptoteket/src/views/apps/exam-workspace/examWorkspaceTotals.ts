/**
 * Non-blocking comparisons of the totals the exam text prints with the
 * editable question points (user ruling 2026-10-17). A difference is a
 * warning that never stops Spara or an export; the workspace derives it live.
 */
import type { NativeExamDocument, NativeExamItem } from "../../../api/examWorkspace";
import { examWorkspaceUnits } from "./examWorkspaceStructure";

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

/** Removes the exam's stored printed total, so the questions' sum stands (no exported text holds the printed total). */
export function withoutExamPrintedTotal(document: NativeExamDocument): NativeExamDocument {
  return { ...document, header: { ...document.header, printed_total: null } };
}

/** Removes this part's stored printed total, so the questions' sum stands (no exported text holds the printed total). */
export function withoutPartPrintedTotal(document: NativeExamDocument, parentId: string): NativeExamDocument {
  return {
    ...document,
    parents: document.parents.map((parent) =>
      parent.parent_id === parentId ? { ...parent, printed_total: null } : parent,
    ),
  };
}

export function examWorkspaceFormatPoints(points: number): string {
  return points.toLocaleString("sv-SE", { maximumFractionDigits: 2 });
}

/**
 * Every decimal the value holds, for a printed number beside a computed one:
 * the rounded `examWorkspaceFormatPoints` would read a third-decimal
 * difference as two equal numbers.
 */
export function examWorkspaceFormatExactPoints(points: number): string {
  return points.toLocaleString("sv-SE", { maximumSignificantDigits: 15 });
}

/**
 * One printed total that differs from its questions' sum: the exam level or
 * one part. `target` is the first question carrying the difference the
 * "Visa frågorna" glyph jumps to, or null when no jump has a useful target.
 */
export type PrintedTotalMismatch =
  | { level: "exam"; printed: number; sum: number; target: string | null }
  | { level: "part"; parentId: string; printed: number; sum: number; target: string | null };

/**
 * The binary-float rule of `examWorkspacePrintedDifference` for one
 * comparison: only accumulated representation error is ignored, never a
 * meaningful difference in the printed score.
 */
function withinPrintedTolerance(a: number, b: number, count: number): boolean {
  const tolerance =
    Number.EPSILON * Math.max(1, Math.abs(a), Math.abs(b)) * Math.max(1, count);
  return Math.abs(a - b) <= tolerance;
}

/** A question that carries a difference: its points are missing, or the source printed another number. */
function printedQuestionDiffers(item: NativeExamItem): boolean {
  if (item.points == null) {
    return true;
  }
  const source = item.source_points ?? null;
  return source !== null && !withinPrintedTolerance(source, item.points, 1);
}

/**
 * One entry per printed total that differs from its questions' sum
 * (TASK-SKRIPT-40-04-10): the exam entry first, then one entry per
 * differing part in document order; empty when nothing differs.
 */
export function examWorkspacePrintedTotalMismatches(
  document: NativeExamDocument,
): PrintedTotalMismatch[] {
  const examSum = document.items.reduce((total, item) => total + (item.points ?? 0), 0);
  const examPrinted = document.header.printed_total ?? null;
  const examDiffers = examWorkspacePrintedDifference(examPrinted, document.items) !== null;

  const parentById = new Map(document.parents.map((parent) => [parent.parent_id, parent]));
  const itemById = new Map(document.items.map((item) => [item.item_id, item]));
  const childrenOf = (itemIds: string[]): NativeExamItem[] =>
    itemIds.flatMap((itemId) => {
      const item = itemById.get(itemId);
      return item === undefined ? [] : [item];
    });

  // The parts in document order; a parent the units never name still counts.
  const orderedParentIds: string[] = [];
  for (const unit of examWorkspaceUnits(document)) {
    if (unit.kind === "parent" && !orderedParentIds.includes(unit.parentId)) {
      orderedParentIds.push(unit.parentId);
    }
  }
  for (const parent of document.parents) {
    if (!orderedParentIds.includes(parent.parent_id)) {
      orderedParentIds.push(parent.parent_id);
    }
  }

  const differingParts = new Map<string, { printed: number; sum: number }>();
  for (const parentId of orderedParentIds) {
    const parent = parentById.get(parentId);
    if (parent?.printed_total == null) {
      continue;
    }
    const children = childrenOf(parent.item_ids);
    if (children.length === 0) {
      continue;
    }
    if (examWorkspacePrintedDifference(parent.printed_total, children) !== null) {
      differingParts.set(parentId, {
        printed: parent.printed_total,
        sum: children.reduce((total, child) => total + (child.points ?? 0), 0),
      });
    }
  }
  if (!examDiffers && differingParts.size === 0) {
    return [];
  }

  const firstDifferingIn = (items: NativeExamItem[]): string | null =>
    items.find((item) => printedQuestionDiffers(item))?.item_id ?? null;
  const examTarget = firstDifferingIn(document.items) ?? [...differingParts.keys()][0] ?? null;

  const mismatches: PrintedTotalMismatch[] = [];
  if (examDiffers && examPrinted !== null) {
    mismatches.push({ level: "exam", printed: examPrinted, sum: examSum, target: examTarget });
  }
  for (const [parentId, part] of differingParts) {
    const parent = parentById.get(parentId);
    mismatches.push({
      level: "part",
      parentId,
      printed: part.printed,
      sum: part.sum,
      target: parent ? firstDifferingIn(childrenOf(parent.item_ids)) : null,
    });
  }
  return mismatches;
}
