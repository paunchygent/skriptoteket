/**
 * R10-2 fail-first: recovery restores a missing part only when this tab
 * owns it (TASK-SKRIPT-40-04-14, rereview 10 R10-2).
 *
 * A title-only edit owns exactly the title piece, so merging it over a
 * newest copy whose part is gone must keep the newest absence. An edit to
 * the part itself owns the part piece, so the deleted part comes back.
 * Ported from the reviewer's intent-neighbours probes, same scenarios,
 * names and assertions.
 */

import { describe, expect, it } from "vitest";

import type {
  NativeExamBodyParagraph,
  NativeExamDocument,
  NativeExamItem,
  NativeExamParent,
} from "../../../api/examWorkspace";
import { newTeacherItem } from "./examWorkspaceItemEdits";
import { diffPieces } from "./examWorkspaceEditPieces";
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
    schema_version: "native_exam_document_v11",
    title: "Original",
    ...overrides,
  };
}

function textInstruction(text: string): NativeExamBodyParagraph[] {
  return [{ heading_level: null, segments: [{ kind: "text", marks: [], text }] }];
}

function baseWithParent(): NativeExamDocument {
  return documentWith(
    [
      { ...newTeacherItem("item_001", 1, "free_text"), points: 2 },
      { ...newTeacherItem("item_002", 2, "free_text"), points: 2 },
    ],
    {
      parents: [
        {
          instruction: textInstruction("Besvara bara den första frågan."),
          item_ids: ["item_001", "item_002"],
          parent_id: "parent_001",
          place: 0,
        },
      ],
    },
  );
}

function instructionOf(document: NativeExamDocument, parentId: string): NativeExamBodyParagraph[] {
  const parent: NativeExamParent | undefined = document.parents.find(
    (entry) => entry.parent_id === parentId,
  );
  if (parent === undefined) {
    throw new Error(`expected ${parentId}`);
  }
  return parent.instruction;
}

describe("mergeRefusedEdit owned parents", () => {
  it("untouched remotely deleted part stays deleted when only the title is locally owned", () => {
    const base = baseWithParent();
    const desired: NativeExamDocument = { ...base, title: "Local title" };
    const fresh: NativeExamDocument = { ...base, parents: [], revision: 2 };
    const owned = diffPieces(base, desired);

    expect([...owned]).toEqual(["title"]);
    const merged = mergeRefusedEdit(desired, owned, fresh);

    expect({ title: merged.title, parents: merged.parents }).toEqual({
      title: "Local title",
      parents: [],
    });
  });

  it("control: locally edited remotely deleted part is restored", () => {
    const base = baseWithParent();
    const desired: NativeExamDocument = {
      ...base,
      parents: base.parents.map((parent) => ({
        ...parent,
        instruction: textInstruction("Local instruction"),
      })),
    };
    const fresh: NativeExamDocument = { ...base, parents: [], revision: 2 };

    const merged = mergeRefusedEdit(desired, diffPieces(base, desired), fresh);

    expect(instructionOf(merged, "parent_001")).toEqual(instructionOf(desired, "parent_001"));
  });

  it("a surviving owned question explicitly standalone in newest does not need its deleted old container", () => {
    const base = baseWithParent();
    const desired: NativeExamDocument = {
      ...base,
      items: base.items.map((item) =>
        item.item_id === "item_001" ? { ...item, points: 7 } : item,
      ),
    };
    const newest: NativeExamDocument = { ...base, parents: [], revision: 2 };
    const owned = diffPieces(base, desired);

    expect([...owned]).toEqual(["question:item_001"]);
    const merged = mergeRefusedEdit(desired, owned, newest);

    expect({
      parents: merged.parents,
      points: merged.items.map((item) => item.points),
    }).toEqual({ parents: [], points: [7, 2] });
  });

  it("control: a remotely removed owned question really needs its restored original container", () => {
    const base = baseWithParent();
    const desired: NativeExamDocument = {
      ...base,
      items: base.items.map((item) =>
        item.item_id === "item_001" ? { ...item, points: 7 } : item,
      ),
    };
    const newest: NativeExamDocument = {
      ...base,
      items: base.items.filter((item) => item.item_id !== "item_001"),
      parents: [],
      revision: 2,
    };

    const merged = mergeRefusedEdit(desired, diffPieces(base, desired), newest);

    expect(merged.items.find((item) => item.item_id === "item_001")?.points).toBe(7);
    expect(
      merged.parents.map((parent) => ({ id: parent.parent_id, items: parent.item_ids })),
    ).toEqual([{ id: "parent_001", items: ["item_001"] }]);
  });

  it("a locally owned move into an existing part retains the required container even without content ownership", () => {
    const grouped = baseWithParent();
    const base: NativeExamDocument = {
      ...grouped,
      parents: grouped.parents.map((parent) => ({ ...parent, item_ids: [] })),
    };
    const desired: NativeExamDocument = {
      ...base,
      parents: base.parents.map((parent) => ({ ...parent, item_ids: ["item_001"] })),
    };
    const newest: NativeExamDocument = { ...base, parents: [], revision: 2 };
    const owned = diffPieces(base, desired);

    expect([...owned]).toEqual(["membership:item_001"]);
    const merged = mergeRefusedEdit(desired, owned, newest);

    expect(
      merged.parents.map((parent) => ({ id: parent.parent_id, items: parent.item_ids })),
    ).toEqual([{ id: "parent_001", items: ["item_001"] }]);
  });
});
