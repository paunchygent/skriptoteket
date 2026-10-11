/**
 * Exam workspace parent presentation.
 *
 * Expected behavior:
 *   A parent's total is the sum of its children's points and is absent when
 *   any child has no points. Only the parent's first child carries the block
 *   (instruction once, total label); every child knows its position; a
 *   standalone item carries neither. A document without parents leaves every
 *   row untouched.
 */

import { describe, expect, it } from "vitest";

import {
  examWorkspaceParentPoints,
  examWorkspaceParentPointsLabel,
} from "./examWorkspaceParents";
import { toExamWorkspaceItemRows } from "./examWorkspaceRows";
import { buildParentDocument } from "./examWorkspaceParentDocument.specSupport";

describe("examWorkspaceParentPoints", () => {
  it("sums the points of the recorded children", () => {
    const document = buildParentDocument();

    expect(examWorkspaceParentPoints(document.parents[0]!, document.items)).toBe(3);
    expect(examWorkspaceParentPointsLabel(3)).toBe("Totalt 3 poäng");
  });

  it("is absent while any child has no points, even when the others have", () => {
    const document = buildParentDocument();
    const items = document.items.map((item) =>
      item.item_id === "item_002" ? { ...item, points: null } : item,
    );

    expect(examWorkspaceParentPoints(document.parents[0]!, items)).toBeNull();
    expect(examWorkspaceParentPointsLabel(null)).toBe("Totalt –");
  });

  it("does not count a standalone item's points into the parent", () => {
    const document = buildParentDocument();
    const items = document.items.map((item) =>
      item.item_id === "item_004" ? { ...item, points: 40 } : item,
    );

    expect(examWorkspaceParentPoints(document.parents[0]!, items)).toBe(3);
  });
});

describe("toExamWorkspaceItemRows with parents", () => {
  it("puts the block on the first child only and positions every child", () => {
    const document = buildParentDocument();
    const rows = toExamWorkspaceItemRows(document.items, document.parents);

    expect(rows.map((row) => row.parentBlock?.parentId ?? null)).toEqual([
      "parent_001",
      null,
      null,
      null,
    ]);
    expect(rows[0]!.parentBlock?.instruction).toEqual(document.parents[0]!.instruction);
    expect(rows[0]!.parentBlock?.pointsLabel).toBe("Totalt 3 poäng");
    expect(rows.map((row) => row.parentChild)).toEqual([
      { childCount: 3, childIndex: 0, parentId: "parent_001" },
      { childCount: 3, childIndex: 1, parentId: "parent_001" },
      { childCount: 3, childIndex: 2, parentId: "parent_001" },
      null,
    ]);
  });

  it("leaves every row without a parent when the document has none", () => {
    const document = buildParentDocument();
    const rows = toExamWorkspaceItemRows(document.items);

    expect(rows.every((row) => row.parentBlock === null && row.parentChild === null)).toBe(true);
  });
});
