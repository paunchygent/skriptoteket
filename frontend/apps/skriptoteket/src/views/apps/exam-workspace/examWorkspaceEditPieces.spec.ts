/**
 * Exam workspace edit pieces: the semantic units `diffPieces` reports.
 *
 * Each unit has its own key; derived sequence numbers, revision and identity
 * metadata and asset declarations never produce a piece.
 */

import { describe, expect, it } from "vitest";

import type {
  NativeExamAsset,
  NativeExamBodyParagraph,
  NativeExamDocument,
  NativeExamItem,
  NativeExamParent,
} from "../../../api/examWorkspace";
import {
  diffPieces,
  EDIT_PIECE_HEADER,
  EDIT_PIECE_INSTRUCTIONS,
  EDIT_PIECE_OUTLINE,
  EDIT_PIECE_QUESTION_ORDER,
  EDIT_PIECE_TITLE,
  membershipPiece,
  parentPiece,
  questionPiece,
} from "./examWorkspaceEditPieces";
import { newTeacherItem } from "./examWorkspaceItemEdits";

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

function baseDocument(): NativeExamDocument {
  return documentWith([
    { ...newTeacherItem("item_001", 1, "free_text"), points: 2 },
    { ...newTeacherItem("item_002", 2, "free_text"), points: 2 },
  ]);
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

function asset(assetId: string): NativeExamAsset {
  return {
    asset_id: assetId,
    byte_length: 1,
    media_type: "image/png",
    sha256: "a".repeat(64),
  };
}

describe("diffPieces", () => {
  it("reports no piece for identical documents", () => {
    expect(diffPieces(baseDocument(), baseDocument()).size).toBe(0);
  });

  it("reports the title, header and instructions as separate pieces", () => {
    const base = baseDocument();
    expect(diffPieces(base, { ...base, title: "Ny titel" })).toEqual(new Set([EDIT_PIECE_TITLE]));
    expect(diffPieces(base, { ...base, header: { tags: [] } })).toEqual(new Set());
    const header = { ...base.header, course_hint: "Matematik 1" };
    expect(diffPieces(base, { ...base, header })).toEqual(new Set([EDIT_PIECE_HEADER]));
    expect(diffPieces(base, { ...base, instructions: textInstruction("Läs först.") })).toEqual(
      new Set([EDIT_PIECE_INSTRUCTIONS]),
    );
  });

  it("reports one piece per changed question and ignores renumbering", () => {
    const base = baseDocument();
    const renumbered: NativeExamDocument = {
      ...base,
      items: base.items.map((item, index) => ({ ...item, sequence: base.items.length - index })),
    };
    expect(diffPieces(base, renumbered).size).toBe(0);
    const changed: NativeExamDocument = {
      ...base,
      items: base.items.map((item) =>
        item.item_id === "item_001" ? { ...item, points: 7 } : item,
      ),
    };
    expect(diffPieces(base, changed)).toEqual(new Set([questionPiece("item_001")]));
  });

  it("reports existence for an added or removed question", () => {
    const base = baseDocument();
    const added: NativeExamDocument = {
      ...base,
      items: [...base.items, { ...newTeacherItem("item_003", 3, "free_text"), points: 4 }],
    };
    expect(diffPieces(base, added)).toEqual(
      new Set([questionPiece("item_003"), EDIT_PIECE_QUESTION_ORDER]),
    );
    const removed: NativeExamDocument = {
      ...base,
      items: base.items.filter((item) => item.item_id !== "item_002"),
    };
    expect(diffPieces(base, removed)).toEqual(
      new Set([questionPiece("item_002"), EDIT_PIECE_QUESTION_ORDER]),
    );
  });

  it("reports the question order separately from content", () => {
    const base = baseDocument();
    const reordered: NativeExamDocument = {
      ...base,
      items: [
        { ...base.items[1], sequence: 1 },
        { ...base.items[0], sequence: 2 },
      ],
    };
    expect(diffPieces(base, reordered)).toEqual(new Set([EDIT_PIECE_QUESTION_ORDER]));
  });

  it("reports one piece per changed or removed parent", () => {
    const base = documentWith(
      [
        { ...newTeacherItem("item_001", 1, "free_text"), points: 2 },
        { ...newTeacherItem("item_002", 2, "free_text"), points: 2 },
      ],
      { parents: [parentOf("parent_001", ["item_001", "item_002"], 0, "Del A")] },
    );
    const renamed: NativeExamDocument = {
      ...base,
      parents: [parentOf("parent_001", ["item_001", "item_002"], 0, "Del A ändrad")],
    };
    expect(diffPieces(base, renamed)).toEqual(new Set([parentPiece("parent_001")]));
    const removed: NativeExamDocument = { ...base, parents: [] };
    expect(diffPieces(base, removed)).toEqual(
      new Set([
        parentPiece("parent_001"),
        membershipPiece("item_001"),
        membershipPiece("item_002"),
        EDIT_PIECE_OUTLINE,
      ]),
    );
  });

  it("reports membership separately from question content", () => {
    const base = documentWith(
      [
        { ...newTeacherItem("item_001", 1, "free_text"), points: 2 },
        { ...newTeacherItem("item_002", 2, "free_text"), points: 2 },
      ],
      { parents: [parentOf("parent_001", ["item_001"], 0, "Del A")] },
    );
    const moved: NativeExamDocument = {
      ...base,
      parents: [parentOf("parent_001", ["item_002"], 0, "Del A")],
    };
    expect(diffPieces(base, moved)).toEqual(new Set([membershipPiece("item_001"), membershipPiece("item_002")]));
    const editedAndMoved: NativeExamDocument = {
      ...moved,
      items: moved.items.map((item) => (item.item_id === "item_001" ? { ...item, points: 5 } : item)),
    };
    expect(diffPieces(base, editedAndMoved)).toEqual(
      new Set([questionPiece("item_001"), membershipPiece("item_001"), membershipPiece("item_002")]),
    );
  });

  it("reports the outline when a block moves, not when only a title changes", () => {
    const base = documentWith(
      [
        { ...newTeacherItem("item_001", 1, "free_text"), points: 2 },
        { ...newTeacherItem("item_002", 2, "free_text"), points: 2 },
      ],
      {
        parents: [
          parentOf("parent_001", [], 0, "Före"),
          parentOf("parent_002", [], 2, "Efter"),
        ],
      },
    );
    const moved: NativeExamDocument = {
      ...base,
      parents: [parentOf("parent_002", [], 2, "Efter"), parentOf("parent_001", [], 0, "Före")],
    };
    expect(diffPieces(base, moved)).toEqual(new Set([EDIT_PIECE_OUTLINE]));
    expect(diffPieces(base, { ...base, title: "Ny titel" })).toEqual(new Set([EDIT_PIECE_TITLE]));
  });

  it("ignores revision, identity metadata and asset declarations", () => {
    const base = documentWith(
      [{ ...newTeacherItem("item_001", 1, "free_text"), points: 2 }],
      { assets: [asset("asset_001")], revision: 3 },
    );
    const meta: NativeExamDocument = {
      ...base,
      assets: [],
      document_id: "00000000-0000-4000-8000-000000000002",
      origin: { kind: "docx_import" },
      revision: 9,
      schema_version: "native_exam_document_v11",
    };
    expect(diffPieces(base, meta).size).toBe(0);
  });

  it("reports no piece when either side is missing", () => {
    expect(diffPieces(null, baseDocument()).size).toBe(0);
    expect(diffPieces(baseDocument(), null).size).toBe(0);
    expect(diffPieces(null, null).size).toBe(0);
  });
});
