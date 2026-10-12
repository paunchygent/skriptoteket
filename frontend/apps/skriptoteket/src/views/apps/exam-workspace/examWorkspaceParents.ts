/**
 * Exam workspace parent presentation.
 *
 * Domain purpose:
 *   A parent is a shared instruction over consecutive child questions of any
 *   mix of kinds, as an Exam.net information block holds questions of any type.
 *   The editor shows the instruction once above the first child with
 *   the parent's points, the sum of its children's points, and tells the
 *   teacher that a child cannot be moved, removed or retyped here. Parent
 *   authoring belongs to ST-SKRIPT-39-06; this module only reads parents.
 *
 * Relationships:
 *   - Mirrors `parent_points` in
 *     `domain/curated_apps/exam_workspace/native_exam_parent.py`.
 *   - Pure functions consumed by `examWorkspaceRows`, `ExamWorkspaceItemTable`
 *     and `ExamWorkspaceItemEditor`.
 *   - Reads shapes from `api/examWorkspace.ts`.
 */

import type { NativeExamItem, NativeExamParent } from "../../../api/examWorkspace";

export const PARENT_HEADING_COPY = "Uppgift med deluppgifter";
export const PARENT_CHILD_LOCKED_COPY =
  "Deluppgifter kan ännu inte flyttas, tas bort eller byta typ här.";

export type ExamWorkspaceParentBlock = {
  instruction: string[];
  parentId: string;
  pointsLabel: string;
};

export type ExamWorkspaceParentChild = {
  childCount: number;
  childIndex: number;
  parentId: string;
};

/** Sum of the children's points; null when any child has no points. */
export function examWorkspaceParentPoints(
  parent: NativeExamParent,
  items: NativeExamItem[],
): number | null {
  const pointsById = new Map(items.map((item) => [item.item_id, item.points ?? null]));
  let total = 0;
  for (const itemId of parent.item_ids) {
    const points = pointsById.get(itemId) ?? null;
    if (points === null) {
      return null;
    }
    total += points;
  }
  return total;
}

/** "Totalt 3 poäng", or "Totalt –" while a child lacks points. */
export function examWorkspaceParentPointsLabel(total: number | null): string {
  if (total === null) {
    return "Totalt –";
  }
  return `Totalt ${total.toLocaleString("sv-SE", { maximumFractionDigits: 2 })} poäng`;
}

/** The block shown above each parent's first child, keyed by that child's item id. */
export function examWorkspaceParentBlocksByFirstChild(
  parents: NativeExamParent[],
  items: NativeExamItem[],
): Record<string, ExamWorkspaceParentBlock> {
  const blocks: Record<string, ExamWorkspaceParentBlock> = {};
  for (const parent of parents) {
    const firstChildId = parent.item_ids[0];
    if (firstChildId === undefined) {
      continue;
    }
    blocks[firstChildId] = {
      instruction: [...parent.instruction],
      parentId: parent.parent_id,
      pointsLabel: examWorkspaceParentPointsLabel(examWorkspaceParentPoints(parent, items)),
    };
  }
  return blocks;
}

/** Where each child sits in its parent, keyed by child item id. */
export function examWorkspaceParentChildren(
  parents: NativeExamParent[],
): Record<string, ExamWorkspaceParentChild> {
  const children: Record<string, ExamWorkspaceParentChild> = {};
  for (const parent of parents) {
    parent.item_ids.forEach((itemId, childIndex) => {
      children[itemId] = {
        childCount: parent.item_ids.length,
        childIndex,
        parentId: parent.parent_id,
      };
    });
  }
  return children;
}
