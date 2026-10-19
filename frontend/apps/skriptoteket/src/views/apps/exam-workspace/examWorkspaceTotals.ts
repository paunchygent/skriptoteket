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

/** One entry of the printed-total account: a differing part, question, or the unexplained rest. */
export type PrintedDifferenceRow =
  | { kind: "part"; parentId: string; printed: number; now: number }
  | { kind: "question"; itemId: string; source: number | null; now: number | null }
  | { kind: "remainder"; points: number };

/** Everything the points note shows: the printed and summed totals with their rows. */
export type PrintedTotalAccount = {
  printed: number | null;
  sum: number;
  rows: PrintedDifferenceRow[];
  dismissed: boolean;
};

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

/** A question the note names: its points are missing, or the source printed another number. */
function printedQuestionDiffers(item: NativeExamItem): boolean {
  if (item.points == null) {
    return true;
  }
  const source = item.source_points ?? null;
  return source !== null && !withinPrintedTolerance(source, item.points, 1);
}

/**
 * The printed-total account behind the points note (TASK-SKRIPT-40-04-10):
 * null when neither the exam total nor any part total differs from the
 * questions' points, else the printed and summed totals with one row per
 * differing part and question in document order and a remainder row for the
 * points no entry explains. Parents are flat, each owning its item ids.
 */
export function examWorkspacePrintedDifferences(
  document: NativeExamDocument,
): PrintedTotalAccount | null {
  const printed = document.header.printed_total ?? null;
  const dismissed = document.header.printed_total_dismissed;
  const sum = document.items.reduce((total, item) => total + (item.points ?? 0), 0);
  const examDiffers = examWorkspacePrintedDifference(printed, document.items) !== null;

  const itemById = new Map(document.items.map((item) => [item.item_id, item]));
  const childrenOf = (itemIds: string[]): NativeExamItem[] =>
    itemIds.flatMap((itemId) => {
      const item = itemById.get(itemId);
      return item === undefined ? [] : [item];
    });
  const differingParts = new Map<string, { printed: number; now: number }>();
  for (const parent of document.parents) {
    if (parent.printed_total == null) {
      continue;
    }
    const children = childrenOf(parent.item_ids);
    if (examWorkspacePrintedDifference(parent.printed_total, children) !== null) {
      differingParts.set(parent.parent_id, {
        now: children.reduce((total, child) => total + (child.points ?? 0), 0),
        printed: parent.printed_total,
      });
    }
  }
  if (!examDiffers && differingParts.size === 0) {
    return null;
  }

  const rows: PrintedDifferenceRow[] = [];
  const questionShare = new Map<string, number>();
  const pushQuestion = (item: NativeExamItem): void => {
    const source = item.source_points ?? null;
    rows.push({ itemId: item.item_id, kind: "question", now: item.points ?? null, source });
    if (source !== null) {
      questionShare.set(item.item_id, source - (item.points ?? 0));
    }
  };
  const itemOrder = new Map(document.items.map((item, index) => [item.item_id, index]));
  for (const unit of examWorkspaceUnits(document)) {
    if (unit.kind === "parent") {
      const part = differingParts.get(unit.parentId);
      if (part !== undefined) {
        rows.push({ kind: "part", now: part.now, parentId: unit.parentId, printed: part.printed });
      }
      childrenOf(unit.itemIds)
        .sort((a, b) => itemOrder.get(a.item_id)! - itemOrder.get(b.item_id)!)
        .filter(printedQuestionDiffers)
        .forEach(pushQuestion);
      continue;
    }
    const item = itemById.get(unit.itemId);
    if (item !== undefined && printedQuestionDiffers(item)) {
      pushQuestion(item);
    }
  }

  if (printed !== null && examDiffers) {
    let explained = 0;
    for (const share of questionShare.values()) {
      explained += share;
    }
    for (const [parentId, part] of differingParts) {
      const parent = document.parents.find((entry) => entry.parent_id === parentId)!;
      let own = 0;
      for (const itemId of parent.item_ids) {
        own += questionShare.get(itemId) ?? 0;
      }
      explained += part.printed - part.now - own;
    }
    const remainder = printed - sum - explained;
    if (!withinPrintedTolerance(remainder, 0, document.items.length)) {
      rows.push({ kind: "remainder", points: remainder });
    }
  }

  return { dismissed, printed, rows, sum };
}
