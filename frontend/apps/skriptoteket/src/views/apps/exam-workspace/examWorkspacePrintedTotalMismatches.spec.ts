/**
 * The printed-total mismatches behind the footer lines.
 *
 * Expected behavior:
 *   `examWorkspacePrintedTotalMismatches` returns one entry per printed
 *   total that differs from its questions' sum: the exam entry first, then
 *   one entry per differing part in document order; empty when nothing
 *   differs. A question carries a difference when its points are null, or
 *   its source_points is non-null and differs from its points (the existing
 *   float tolerance). The exam target is the first such question in
 *   document order, else the first differing part's id, else null. A part
 *   target is the first such question among that part's own questions, else
 *   null.
 */

import { describe, expect, it } from "vitest";

import type {
  NativeExamDocument,
  NativeExamItem,
  NativeExamParent,
} from "../../../api/examWorkspace";
import { newTeacherItem } from "./examWorkspaceItemEdits";
import type { PrintedTotalMismatch } from "./examWorkspaceTotals";
import {
  examWorkspaceFormatExactPoints,
  examWorkspacePrintedTotalMismatches,
} from "./examWorkspaceTotals";

function question(
  itemId: string,
  sequence: number,
  points: number | null,
  source: number | null,
): NativeExamItem {
  return { ...newTeacherItem(itemId, sequence, "free_text"), points, source_points: source };
}

function part(
  parentId: string,
  place: number,
  itemIds: string[],
  printed: number | null = null,
): NativeExamParent {
  return { instruction: [], item_ids: itemIds, parent_id: parentId, place, printed_total: printed };
}

function documentOf(
  items: NativeExamItem[],
  parents: NativeExamParent[],
  printed: number | null,
): NativeExamDocument {
  return {
    assets: [],
    document_id: "00000000-0000-4000-8000-000000000001",
    header: { printed_total: printed, tags: [] },
    instructions: [],
    items,
    origin: { kind: "created" },
    parents,
    revision: 1,
    schema_version: "native_exam_document_v9",
    title: "Prov",
  };
}

describe("examWorkspacePrintedTotalMismatches", () => {
  it("keeps every decimal instead of rounding to two", () => {
    expect(examWorkspaceFormatExactPoints(12.001)).toBe("12,001");
    expect(examWorkspaceFormatExactPoints(0.1 + 0.2)).toBe("0,3");
    expect(examWorkspaceFormatExactPoints(67)).toBe("67");
  });

  it("returns empty when nothing differs", () => {
    const document = documentOf(
      [question("item_001", 1, 10, 10), question("item_002", 2, 10, 10)],
      [],
      20,
    );

    expect(examWorkspacePrintedTotalMismatches(document)).toEqual([]);
  });

  it("returns empty when no total is printed", () => {
    const document = documentOf(
      [question("item_001", 1, 10, 10), question("item_002", 2, 10, 10)],
      [],
      null,
    );

    expect(examWorkspacePrintedTotalMismatches(document)).toEqual([]);
  });

  it("names the exam difference with the first differing question as target", () => {
    const document = documentOf(
      [
        question("item_001", 1, 10, 10),
        question("item_002", 2, 9, 12),
        question("item_003", 3, null, 4),
      ],
      [],
      70,
    );

    const mismatches: PrintedTotalMismatch[] = examWorkspacePrintedTotalMismatches(document);
    expect(mismatches).toHaveLength(1);
    expect(mismatches[0]).toEqual({ level: "exam", printed: 70, sum: 19, target: "item_002" });
  });

  it("names a part-only mismatch with the part's own first differing question", () => {
    const document = documentOf(
      [question("item_001", 1, 2, 2), question("item_002", 2, null, 3)],
      [part("parent_001", 0, ["item_001", "item_002"], 8)],
      null,
    );

    expect(examWorkspacePrintedTotalMismatches(document)).toEqual([
      { level: "part", parentId: "parent_001", printed: 8, sum: 2, target: "item_002" },
    ]);
  });

  it("lists the exam first, then each differing part in document order", () => {
    const document = documentOf(
      [
        question("item_001", 1, 10, 12),
        question("item_002", 2, 10, 10),
        question("item_003", 3, 5, 5),
        question("item_004", 4, 5, 5),
      ],
      [
        part("parent_001", 0, ["item_001", "item_002"], 22),
        part("parent_002", 2, ["item_003", "item_004"], 12),
      ],
      70,
    );

    expect(examWorkspacePrintedTotalMismatches(document)).toEqual([
      { level: "exam", printed: 70, sum: 30, target: "item_001" },
      { level: "part", parentId: "parent_001", printed: 22, sum: 20, target: "item_001" },
      { level: "part", parentId: "parent_002", printed: 12, sum: 10, target: null },
    ]);
  });

  it("falls back to the first differing part when no question carries the exam difference", () => {
    const document = documentOf(
      [question("item_001", 1, 30, 30), question("item_002", 2, 37, 37)],
      [part("parent_001", 0, ["item_001"], 31)],
      70,
    );

    expect(examWorkspacePrintedTotalMismatches(document)).toEqual([
      { level: "exam", printed: 70, sum: 67, target: "parent_001" },
      { level: "part", parentId: "parent_001", printed: 31, sum: 30, target: null },
    ]);
  });

  it("has no target when neither a question nor a part carries the difference", () => {
    const document = documentOf(
      [question("item_001", 1, 30, 30), question("item_002", 2, 37, 37)],
      [],
      70,
    );

    expect(examWorkspacePrintedTotalMismatches(document)).toEqual([
      { level: "exam", printed: 70, sum: 67, target: null },
    ]);
  });

  it("ignores binary float noise", () => {
    const document = documentOf(
      [question("item_001", 1, 0.1, 0.1), question("item_002", 2, 0.2, 0.2)],
      [],
      0.3,
    );

    expect(examWorkspacePrintedTotalMismatches(document)).toEqual([]);
  });

  it("gives no entry for a question whose source printed nothing", () => {
    const document = documentOf([question("item_001", 1, 5, null)], [], 5);

    expect(examWorkspacePrintedTotalMismatches(document)).toEqual([]);
  });

  it("treats a printed zero as a real total", () => {
    const document = documentOf([question("item_001", 1, 5, 5)], [], 0);

    const mismatches = examWorkspacePrintedTotalMismatches(document);
    expect(mismatches).toEqual([{ level: "exam", printed: 0, sum: 5, target: null }]);
  });

  it("emits no part mismatch for a childless instruction block keeping its printed total", () => {
    const document = documentOf(
      [
        question("item_001", 1, 10, 10),
        question("item_002", 2, 5, 5),
        question("item_003", 3, 5, 5),
      ],
      [
        part("parent_001", 0, [], 8),
        part("parent_002", 1, ["item_002", "item_003"], 12),
      ],
      30,
    );

    expect(examWorkspacePrintedTotalMismatches(document)).toEqual([
      { level: "exam", printed: 30, sum: 20, target: "parent_002" },
      { level: "part", parentId: "parent_002", printed: 12, sum: 10, target: null },
    ]);
  });
});
