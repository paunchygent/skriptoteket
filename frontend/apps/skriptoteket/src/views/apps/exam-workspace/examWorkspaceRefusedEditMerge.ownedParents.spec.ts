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
    schema_version: "native_exam_document_v10",
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
});
