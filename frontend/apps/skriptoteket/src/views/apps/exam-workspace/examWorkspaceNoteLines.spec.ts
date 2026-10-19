import { describe, expect, it } from "vitest";

import type { NativeExamDocument } from "../../../api/examWorkspace";
import { newTeacherItem } from "./examWorkspaceItemEdits";
import { examWorkspaceListEntries } from "./examWorkspaceListEntries";
import { buildExamWorkspaceNoteLines } from "./examWorkspaceNoteLines";
import type { ExamWorkspaceListEntry } from "./examWorkspaceListEntries";
import type { PrintedTotalMismatch } from "./examWorkspaceTotals";
import { examWorkspacePrintedTotalMismatches } from "./examWorkspaceTotals";

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

  it("skips a childless instruction block with an empty list label", () => {
    const mismatches: PrintedTotalMismatch[] = [
      { level: "part", parentId: "parent_001", printed: 8, sum: 0, target: null },
    ];
    const entries = [parentEntry("parent_001", "")];
    expect(buildExamWorkspaceNoteLines(mismatches, entries)).toEqual([]);
  });

  it("renders no line for a deleted last child while keeping a neighbouring part line", () => {
    const document: NativeExamDocument = {
      assets: [],
      document_id: "00000000-0000-4000-8000-000000000001",
      header: { printed_total: 30, tags: [] },
      instructions: [],
      items: [
        { ...newTeacherItem("item_001", 1, "free_text"), points: 10, source_points: 10 },
        { ...newTeacherItem("item_002", 2, "free_text"), points: 5, source_points: 5 },
        { ...newTeacherItem("item_003", 3, "free_text"), points: 5, source_points: 5 },
      ],
      origin: { kind: "created" },
      parents: [
        { instruction: [], item_ids: [], parent_id: "parent_001", place: 0, printed_total: 8 },
        {
          instruction: [],
          item_ids: ["item_002", "item_003"],
          parent_id: "parent_002",
          place: 1,
          printed_total: 12,
        },
      ],
      revision: 1,
      schema_version: "native_exam_document_v10",
      title: "Prov",
    };

    const mismatches = examWorkspacePrintedTotalMismatches(document);
    const entries = examWorkspaceListEntries(document, {}, new Set());
    const lines = buildExamWorkspaceNoteLines(mismatches, entries);

    expect(mismatches.some((entry) => entry.level === "part" && entry.parentId === "parent_001")).toBe(
      false,
    );
    expect(lines.map((line) => line.key)).toEqual(["exam", "part-parent_002"]);
    expect(lines[0]!.target).toBe("parent_002");
    expect(lines[1]!.text).toBe("Del 2 i provtexten säger 12 p, frågorna ger 10 p.");
  });
});
