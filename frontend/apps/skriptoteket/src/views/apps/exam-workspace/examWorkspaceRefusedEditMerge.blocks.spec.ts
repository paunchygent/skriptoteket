/**
 * Exam workspace refused-edit merge: childless instruction block order
 * (TASK-SKRIPT-40-04-14, rereview S4 of repair RM).
 *
 * The kept edit wins where it changed the block order or placement; otherwise
 * the newest order wins. Base-first map order is never the outline order.
 */

import { describe, expect, it } from "vitest";

import type {
  NativeExamBodyParagraph,
  NativeExamDocument,
  NativeExamItem,
  NativeExamParent,
} from "../../../api/examWorkspace";
import { newTeacherItem } from "./examWorkspaceItemEdits";
import { mergeRefusedEdit } from "./examWorkspaceRefusedEditMerge";

function documentWith(items: NativeExamItem[], overrides: Partial<NativeExamDocument> = {}): NativeExamDocument {
  return {
    assets: [],
    document_id: "00000000-0000-4000-8000-000000000001",
    header: { tags: [] },
    instructions: [],
    items,
    origin: { kind: "created" },
    parents: [],
    revision: 1,
    schema_version: "native_exam_document_v10",
    title: "Original",
    ...overrides,
  };
}

function requireMerged(merged: NativeExamDocument | null): NativeExamDocument {
  if (merged === null) {
    throw new Error("expected a merged document");
  }
  return merged;
}

function textInstruction(text: string): NativeExamBodyParagraph[] {
  return [{ heading_level: null, segments: [{ kind: "text", marks: [], text }] }];
}

function parentOf(
  parentId: string,
  itemIds: string[],
  place: number,
  text: string,
): NativeExamParent {
  return { instruction: textInstruction(text), item_ids: itemIds, parent_id: parentId, place };
}

function blockBase(): NativeExamDocument {
  return documentWith(
    [
      { ...newTeacherItem("item_001", 1, "free_text"), points: 2 },
      { ...newTeacherItem("item_002", 2, "free_text"), points: 2 },
    ],
    {
      parents: [
        parentOf("parent_001", [], 2, "Del A: läs först."),
        parentOf("parent_002", [], 2, "Del B: läs sedan."),
      ],
    },
  );
}

describe("mergeRefusedEdit childless block order", () => {
  it("keeps a newest-only reorder of equal-place blocks the edit left untouched", () => {
    const base = blockBase();
    const edited: NativeExamDocument = { ...base, title: "Kept title" };
    const newest: NativeExamDocument = {
      ...base,
      parents: [base.parents[1], base.parents[0]],
    };

    const merged = requireMerged(mergeRefusedEdit(base, edited, newest));

    expect(merged.parents.map((parent) => parent.parent_id)).toEqual([
      "parent_002",
      "parent_001",
    ]);
  });

  it("keeps the edit order when only the edit reordered equal-place blocks", () => {
    const base = blockBase();
    const edited: NativeExamDocument = {
      ...base,
      parents: [base.parents[1], base.parents[0]],
    };
    const newest: NativeExamDocument = { ...base, title: "Remote title" };

    const merged = requireMerged(mergeRefusedEdit(base, edited, newest));

    expect(merged.parents.map((parent) => parent.parent_id)).toEqual([
      "parent_002",
      "parent_001",
    ]);
  });
});
