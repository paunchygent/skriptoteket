import { describe, expect, it } from "vitest";

import { buildExamWorkspaceNoteLines } from "./examWorkspaceNoteLines";
import type { ExamWorkspaceListEntry } from "./examWorkspaceListEntries";
import type { PrintedTotalMismatch } from "./examWorkspaceTotals";

function parentEntry(id: string, label: string): ExamWorkspaceListEntry {
  return { childIds: [], id, kind: "parent", label, points: 0, text: "" };
}

describe("buildExamWorkspaceNoteLines", () => {
  it("builds the exam line text", () => {
    const mismatches: PrintedTotalMismatch[] = [
      { level: "exam", printed: 70, sum: 67, target: "item_001" },
    ];
    expect(buildExamWorkspaceNoteLines(mismatches, [])).toEqual([
      {
        key: "exam",
        kind: "printed-total",
        parentId: null,
        sum: 67,
        target: "item_001",
        text: "Provtexten säger 70 p, frågorna ger 67 p.",
      },
    ]);
  });

  it("names a part line with Del and the list label", () => {
    const mismatches: PrintedTotalMismatch[] = [
      { level: "part", parentId: "parent_001", printed: 22, sum: 20, target: "item_003" },
    ];
    const entries = [parentEntry("parent_001", "1")];
    expect(buildExamWorkspaceNoteLines(mismatches, entries)).toEqual([
      {
        key: "part-parent_001",
        kind: "printed-total",
        parentId: "parent_001",
        sum: 20,
        target: "item_003",
        text: "Del 1 i provtexten säger 22 p, frågorna ger 20 p.",
      },
    ]);
  });

  it("skips a part the list never names", () => {
    const mismatches: PrintedTotalMismatch[] = [
      { level: "part", parentId: "parent_999", printed: 8, sum: 5, target: null },
    ];
    expect(buildExamWorkspaceNoteLines(mismatches, [])).toEqual([]);
  });

  it("prints a third decimal instead of two equal numbers", () => {
    const mismatches: PrintedTotalMismatch[] = [
      { level: "exam", printed: 12.001, sum: 12, target: "item_001" },
    ];
    expect(buildExamWorkspaceNoteLines(mismatches, [])[0]!.text).toBe(
      "Provtexten säger 12,001 p, frågorna ger 12 p.",
    );
  });

  it("orders the exam line first, then parts in mismatch order", () => {
    const mismatches: PrintedTotalMismatch[] = [
      { level: "exam", printed: 70, sum: 30, target: "item_002" },
      { level: "part", parentId: "parent_001", printed: 22, sum: 20, target: "item_001" },
      { level: "part", parentId: "parent_002", printed: 12, sum: 10, target: "item_003" },
    ];
    const entries = [parentEntry("parent_001", "1"), parentEntry("parent_002", "2")];
    expect(buildExamWorkspaceNoteLines(mismatches, entries).map((line) => line.key)).toEqual([
      "exam",
      "part-parent_001",
      "part-parent_002",
    ]);
  });
});
