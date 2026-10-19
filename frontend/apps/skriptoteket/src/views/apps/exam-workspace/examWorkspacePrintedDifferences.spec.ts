/**
 * The printed-total account behind the points note.
 *
 * Expected behavior:
 *   `examWorkspacePrintedDifferences` returns null when neither the exam
 *   total nor any part total differs from the questions' points, and otherwise
 *   returns the printed and summed totals with one row per differing part and
 *   question in document order plus a remainder row for points no entry
 *   explains. Every comparison uses the binary-float tolerance, so decimals
 *   and representation noise never create a row.
 */

import { describe, expect, it } from "vitest";

import type {
  NativeExamDocument,
  NativeExamItem,
  NativeExamParent,
} from "../../../api/examWorkspace";
import { newTeacherItem } from "./examWorkspaceItemEdits";
import type { PrintedTotalAccount } from "./examWorkspaceTotals";
import { examWorkspaceFormatExactPoints, examWorkspacePrintedDifferences } from "./examWorkspaceTotals";

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
  dismissed = false,
): NativeExamDocument {
  return {
    assets: [],
    document_id: "00000000-0000-4000-8000-000000000001",
    header: { printed_total: printed, printed_total_dismissed: dismissed, tags: [] },
    instructions: [],
    items,
    origin: { kind: "created" },
    parents,
    revision: 1,
    schema_version: "native_exam_document_v9",
    title: "Prov",
  };
}

function accountOf(
  printed: number | null,
  sum: number,
  rows: PrintedTotalAccount["rows"],
  dismissed = false,
): PrintedTotalAccount {
  return { dismissed, printed, rows, sum };
}

describe("examWorkspacePrintedDifferences", () => {
  it("keeps every decimal instead of rounding to two", () => {
    expect(examWorkspaceFormatExactPoints(12.001)).toBe("12,001");
    expect(examWorkspaceFormatExactPoints(0.1 + 0.2)).toBe("0,3");
    expect(examWorkspaceFormatExactPoints(67)).toBe("67");
  });

  it("returns null when nothing differs", () => {
    const document = documentOf(
      [question("item_001", 1, 10, 10), question("item_002", 2, 10, 10)],
      [],
      20,
    );

    expect(examWorkspacePrintedDifferences(document)).toBeNull();
  });

  it("returns null when no total is printed", () => {
    const document = documentOf(
      [question("item_001", 1, 10, 10), question("item_002", 2, 10, 10)],
      [],
      null,
    );

    expect(examWorkspacePrintedDifferences(document)).toBeNull();
  });

  it("lists a part, its changed question and a standalone missing question in order", () => {
    const document = documentOf(
      [
        question("item_001", 1, 10, 12),
        question("item_002", 2, 10, 10),
        question("item_003", 3, null, 4),
      ],
      [part("parent_001", 0, ["item_001", "item_002"], 22)],
      70,
    );

    expect(examWorkspacePrintedDifferences(document)).toEqual(
      accountOf(70, 20, [
        { kind: "part", now: 20, parentId: "parent_001", printed: 22 },
        { kind: "question", itemId: "item_001", now: 10, source: 12 },
        { kind: "question", itemId: "item_003", now: null, source: 4 },
        { kind: "remainder", points: 44 },
      ]),
    );
  });

  it("gives only a remainder row when the source contradicts itself", () => {
    const document = documentOf(
      [question("item_001", 1, 30, 30), question("item_002", 2, 37, 37)],
      [],
      70,
    );

    expect(examWorkspacePrintedDifferences(document)).toEqual(
      accountOf(70, 67, [{ kind: "remainder", points: 3 }]),
    );
  });

  it("ignores decimals and binary float noise", () => {
    const decimals = documentOf(
      [question("item_001", 1, 2.5, 2.5), question("item_002", 2, 5, 5)],
      [],
      7.5,
    );
    const noise = documentOf(
      [question("item_001", 1, 0.1, 0.1), question("item_002", 2, 0.2, 0.2)],
      [],
      0.3,
    );

    expect(examWorkspacePrintedDifferences(decimals)).toBeNull();
    expect(examWorkspacePrintedDifferences(noise)).toBeNull();
  });

  it("gives no row for a question whose source printed nothing", () => {
    const document = documentOf([question("item_001", 1, 5, null)], [], 5);

    expect(examWorkspacePrintedDifferences(document)).toBeNull();
  });

  it("lists a question missing both values beside the unexplained remainder", () => {
    const document = documentOf(
      [question("item_001", 1, null, null), question("item_002", 2, 10, 10)],
      [],
      12,
    );

    expect(examWorkspacePrintedDifferences(document)).toEqual(
      accountOf(12, 10, [
        { kind: "question", itemId: "item_001", now: null, source: null },
        { kind: "remainder", points: 2 },
      ]),
    );
  });

  it("gives a part row and no remainder when the exam total matches", () => {
    const document = documentOf(
      [question("item_001", 1, 10, 10), question("item_002", 2, 10, 10)],
      [part("parent_001", 0, ["item_001", "item_002"], 22)],
      20,
    );

    expect(examWorkspacePrintedDifferences(document)).toEqual(
      accountOf(20, 20, [{ kind: "part", now: 20, parentId: "parent_001", printed: 22 }]),
    );
  });

  it("reports dismissed without changing the rows", () => {
    const rows: PrintedTotalAccount["rows"] = [
      { kind: "part", now: 20, parentId: "parent_001", printed: 22 },
      { kind: "question", itemId: "item_001", now: 10, source: 12 },
      { kind: "question", itemId: "item_003", now: null, source: 4 },
      { kind: "remainder", points: 44 },
    ];
    const document = documentOf(
      [
        question("item_001", 1, 10, 12),
        question("item_002", 2, 10, 10),
        question("item_003", 3, null, 4),
      ],
      [part("parent_001", 0, ["item_001", "item_002"], 22)],
      70,
      true,
    );

    expect(examWorkspacePrintedDifferences(document)).toEqual(accountOf(70, 20, rows, true));
  });
});
