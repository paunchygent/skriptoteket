/**
 * The question list gives no number to a childless part.
 *
 * Expected behavior:
 *   Only a unit that holds at least one question takes a number. An instruction
 *   with no questions is an unnumbered row with no children, points 0 and no
 *   printed total, so the questions after it keep their own numbering.
 */

import { describe, expect, it } from "vitest";

import type {
  NativeExamDocument,
  NativeExamItem,
  NativeExamParent,
} from "../../../api/examWorkspace";
import { newTeacherItem } from "./examWorkspaceItemEdits";
import { examWorkspaceListEntries } from "./examWorkspaceListEntries";

function question(sequence: number): NativeExamItem {
  return newTeacherItem(`item_${String(sequence).padStart(3, "0")}`, sequence, "free_text");
}

const document: NativeExamDocument = {
  assets: [],
  document_id: "00000000-0000-4000-8000-000000000001",
  header: { printed_total_dismissed: false, tags: [] },
  instructions: [],
  items: [question(1), question(2), question(3), question(4)],
  origin: { kind: "created" },
  parents: [
    { instruction: [], item_ids: [], parent_id: "parent_001", place: 1 },
    { instruction: [], item_ids: ["item_003", "item_004"], parent_id: "parent_002", place: 2 },
  ] satisfies NativeExamParent[],
  revision: 1,
  schema_version: "native_exam_document_v9",
  title: "Prov",
};

describe("examWorkspaceListEntries with a childless part", () => {
  it("numbers only the units that hold a question", () => {
    const entries = examWorkspaceListEntries(document, {}, new Set());

    expect(entries.map((entry) => entry.label)).toEqual(["1", "", "2", "3", "3a", "3b"]);
  });

  it("keeps the childless part an empty parent row", () => {
    const entries = examWorkspaceListEntries(document, {}, new Set());
    const block = entries[1]!;

    expect(block).toMatchObject({
      childIds: [],
      id: "parent_001",
      kind: "parent",
      label: "",
      points: 0,
    });
  });

  it("names each question's kind on its row", () => {
    const entries = examWorkspaceListEntries(document, {}, new Set());
    const kinds = entries.flatMap((entry) => (entry.kind === "item" ? [entry.itemKind] : []));

    expect(kinds).toEqual(["free_text", "free_text", "free_text", "free_text"]);
  });
});
