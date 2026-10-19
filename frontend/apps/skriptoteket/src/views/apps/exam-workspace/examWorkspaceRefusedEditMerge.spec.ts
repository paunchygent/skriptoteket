/**
 * Exam workspace refused-edit merge: a refused edit survives the takeover
 * (TASK-SKRIPT-40-04-14, USER decision 2026-10-19 "Ta över keeps the edit").
 *
 * Expected behavior:
 *   mergeRefusedEdit(base, edited, newest) returns the document to install
 *   after the tab gets the lease back. Every piece the edit changed from the
 *   base keeps the edited version (the kept edit wins); every untouched piece
 *   keeps the newest version. Items merge by item_id; order follows the edit
 *   only when the edit reordered, otherwise the newest order. Revision,
 *   document_id, origin and schema_version come from newest. No change in the
 *   edit returns null.
 */

import { describe, expect, it } from "vitest";

import type { NativeExamDocument, NativeExamItem } from "../../../api/examWorkspace";
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
    schema_version: "native_exam_document_v9",
    title: "Original",
    ...overrides,
  };
}

function baseDocument(): NativeExamDocument {
  return documentWith([
    { ...newTeacherItem("item_001", 1, "free_text"), points: 2 },
    { ...newTeacherItem("item_002", 2, "free_text"), points: 2 },
  ]);
}

function requireMerged(merged: NativeExamDocument | null): NativeExamDocument {
  if (merged === null) {
    throw new Error("expected a merged document");
  }
  return merged;
}

function itemById(document: NativeExamDocument, itemId: string): NativeExamItem {
  const found = document.items.find((item) => item.item_id === itemId);
  if (found === undefined) {
    throw new Error(`expected ${itemId}`);
  }
  return found;
}

function itemIds(document: NativeExamDocument): string[] {
  return document.items.map((item) => item.item_id);
}

function withPoints(document: NativeExamDocument, itemId: string, points: number): NativeExamDocument {
  return {
    ...document,
    items: document.items.map((item) => (item.item_id === itemId ? { ...item, points } : item)),
  };
}

describe("mergeRefusedEdit", () => {
  it("returns null when the edit changed nothing", () => {
    const base = baseDocument();
    const edited: NativeExamDocument = { ...base, revision: base.revision };
    const newest = withPoints(base, "item_001", 9);

    expect(mergeRefusedEdit(base, edited, newest)).toBeNull();
  });

  it("lets the edit win on a question both tabs changed, and keeps newest elsewhere", () => {
    const base = baseDocument();
    const edited = withPoints(base, "item_001", 7);
    const newest = withPoints(withPoints(base, "item_001", 5), "item_002", 9);

    const merged = requireMerged(mergeRefusedEdit(base, edited, newest));

    expect(itemById(merged, "item_001").points).toBe(7);
    expect(itemById(merged, "item_002").points).toBe(9);
  });

  it("keeps an item the edit added", () => {
    const base = baseDocument();
    const added: NativeExamItem = { ...newTeacherItem("item_003", 3, "free_text"), points: 4 };
    const edited: NativeExamDocument = { ...base, items: [...base.items, added] };
    const newest = withPoints(base, "item_002", 9);

    const merged = requireMerged(mergeRefusedEdit(base, edited, newest));

    expect(itemById(merged, "item_003").points).toBe(4);
    expect(itemById(merged, "item_002").points).toBe(9);
  });

  it("drops an item the edit removed when it is still present", () => {
    const base = baseDocument();
    const edited: NativeExamDocument = {
      ...base,
      items: base.items.filter((item) => item.item_id !== "item_002"),
    };
    const newest = withPoints(base, "item_002", 9);

    const merged = requireMerged(mergeRefusedEdit(base, edited, newest));

    expect(itemIds(merged)).toEqual(["item_001"]);
  });

  it("adds back an item the edit changed but the other tab deleted", () => {
    const base = baseDocument();
    const edited = withPoints(base, "item_002", 7);
    const newest: NativeExamDocument = {
      ...base,
      items: base.items.filter((item) => item.item_id !== "item_002"),
    };

    const merged = requireMerged(mergeRefusedEdit(base, edited, newest));

    expect(itemById(merged, "item_002").points).toBe(7);
  });

  it("uses the edited order when the edit reordered, appending newest-only items", () => {
    const base = baseDocument();
    const edited: NativeExamDocument = { ...base, items: [base.items[1], base.items[0]] };
    const added: NativeExamItem = { ...newTeacherItem("item_003", 3, "free_text"), points: 4 };
    const newest: NativeExamDocument = { ...base, items: [...base.items, added] };

    const merged = requireMerged(mergeRefusedEdit(base, edited, newest));

    expect(itemIds(merged)).toEqual(["item_002", "item_001", "item_003"]);
  });

  it("keeps the newest order when the edit did not reorder", () => {
    const base = baseDocument();
    const edited = withPoints(base, "item_001", 7);
    const newest: NativeExamDocument = { ...base, items: [base.items[1], base.items[0]] };

    const merged = requireMerged(mergeRefusedEdit(base, edited, newest));

    expect(itemIds(merged)).toEqual(["item_002", "item_001"]);
    expect(itemById(merged, "item_001").points).toBe(7);
  });

  it("merges title and header by the same rule and keeps newest identity fields", () => {
    const base = baseDocument();
    const edited: NativeExamDocument = { ...base, title: "Min titel" };
    const newest: NativeExamDocument = {
      ...base,
      header: { ...base.header, course_hint: "Matematik 1" },
      title: "Andra flikens titel",
      revision: 5,
    };

    const merged = requireMerged(mergeRefusedEdit(base, edited, newest));

    expect(merged.title).toBe("Min titel");
    expect(merged.header.course_hint).toBe("Matematik 1");
    expect(merged.revision).toBe(5);
    expect(merged.document_id).toBe(newest.document_id);
    expect(merged.origin).toEqual(newest.origin);
    expect(merged.schema_version).toBe(newest.schema_version);
  });
});
