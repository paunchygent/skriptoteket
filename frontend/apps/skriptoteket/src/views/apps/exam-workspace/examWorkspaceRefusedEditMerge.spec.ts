/**
 * Exam workspace refused-edit merge: a refused edit survives the takeover
 * (TASK-SKRIPT-40-04-14, USER decision 2026-10-19 "Ta över keeps the edit").
 *
 * Expected behavior:
 *   mergeRefusedEdit(desired, owned, newest) returns the document to install
 *   after the tab gets the lease back. Every owned piece keeps the desired
 *   version (the kept edit wins); every other piece keeps the newest
 *   version. The specs derive the owned set with diffPieces(base, edited);
 *   that derivation never runs in production. Items merge by item_id; order follows the edit
 *   only when the edit reordered, otherwise the newest order. Revision,
 *   document_id, origin and schema_version come from newest. No change in the
 *   edit returns null.
 */

import { describe, expect, it } from "vitest";

import type {
  NativeExamAsset,
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

function baseDocument(): NativeExamDocument {
  return documentWith([
    { ...newTeacherItem("item_001", 1, "free_text"), points: 2 },
    { ...newTeacherItem("item_002", 2, "free_text"), points: 2 },
  ]);
}

/** The production call with the spec's owned pieces derived from the edit. */
function mergeKept(
  base: NativeExamDocument,
  edited: NativeExamDocument,
  newest: NativeExamDocument,
): NativeExamDocument {
  return mergeRefusedEdit(edited, diffPieces(base, edited), newest);
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

function asset(assetId: string): NativeExamAsset {
  return {
    asset_id: assetId,
    byte_length: 1,
    media_type: "image/png",
    sha256: "a".repeat(64),
  };
}

function pictureBody(assetId: string): NativeExamItem["body"] {
  return [{ heading_level: null, segments: [{ kind: "asset", asset_id: assetId }] }];
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

function bodyAssetIds(body: NativeExamBodyParagraph[]): string[] {
  return body.flatMap((paragraph) =>
    paragraph.segments.flatMap((segment) => (segment.kind === "asset" ? [segment.asset_id] : [])),
  );
}

/** Mirrors the server's document invariants: contiguous sequences, no unknown or orphan assets, no dangling parent children. */
function assertValidDocument(document: NativeExamDocument): void {
  expect(document.items.map((item) => item.sequence)).toEqual(
    document.items.map((_item, index) => index + 1),
  );
  const itemIds = new Set(document.items.map((item) => item.item_id));
  const referenced = new Set<string>([
    ...document.items.flatMap((item) => bodyAssetIds(item.body)),
    ...bodyAssetIds(document.instructions),
    ...document.parents.flatMap((parent) => bodyAssetIds(parent.instruction)),
  ]);
  const declared = new Set(document.assets.map((entry) => entry.asset_id));
  for (const assetId of referenced) {
    expect(declared.has(assetId)).toBe(true);
  }
  for (const assetId of declared) {
    expect(referenced.has(assetId)).toBe(true);
  }
  const order = new Map(document.items.map((item, index) => [item.item_id, index]));
  let previousPlace: number | null = null;
  for (const parent of document.parents) {
    for (const itemId of parent.item_ids) {
      expect(itemIds.has(itemId)).toBe(true);
    }
    if (previousPlace !== null) {
      expect(parent.place).toBeGreaterThanOrEqual(previousPlace);
    }
    previousPlace = parent.place;
    if (parent.item_ids.length > 0) {
      const first = order.get(parent.item_ids[0]);
      const last = order.get(parent.item_ids[parent.item_ids.length - 1]);
      if (first === undefined || last === undefined) {
        throw new Error("expected parent children in item order");
      }
      expect(parent.place).toBe(first);
      expect(last - first + 1).toBe(parent.item_ids.length);
      parent.item_ids.forEach((itemId, offset) => {
        expect(order.get(itemId)).toBe(first + offset);
      });
    }
  }
  for (const tag of document.header.tags) {
    for (const questionId of tag.question_ids) {
      expect(itemIds.has(questionId)).toBe(true);
    }
  }
}

describe("mergeRefusedEdit", () => {
  it("returns the newest copy when the edit changed nothing", () => {
    const base = baseDocument();
    const edited: NativeExamDocument = { ...base, revision: base.revision };
    const newest = withPoints(base, "item_001", 9);

    expect(mergeKept(base, edited, newest)).toBe(newest);
  });

  it("lets the edit win on a question both tabs changed, and keeps newest elsewhere", () => {
    const base = baseDocument();
    const edited = withPoints(base, "item_001", 7);
    const newest = withPoints(withPoints(base, "item_001", 5), "item_002", 9);

    const merged = mergeKept(base, edited, newest);

    expect(itemById(merged, "item_001").points).toBe(7);
    expect(itemById(merged, "item_002").points).toBe(9);
    assertValidDocument(merged);
  });

  it("keeps an item the edit added", () => {
    const base = baseDocument();
    const added: NativeExamItem = { ...newTeacherItem("item_003", 3, "free_text"), points: 4 };
    const edited: NativeExamDocument = { ...base, items: [...base.items, added] };
    const newest = withPoints(base, "item_002", 9);

    const merged = mergeKept(base, edited, newest);

    expect(itemById(merged, "item_003").points).toBe(4);
    expect(itemById(merged, "item_002").points).toBe(9);
    assertValidDocument(merged);
  });

  it("drops an item the edit removed when it is still present", () => {
    const base = baseDocument();
    const edited: NativeExamDocument = {
      ...base,
      items: base.items.filter((item) => item.item_id !== "item_002"),
    };
    const newest = withPoints(base, "item_002", 9);

    const merged = mergeKept(base, edited, newest);

    expect(itemIds(merged)).toEqual(["item_001"]);
    assertValidDocument(merged);
  });

  it("adds back an item the edit changed but the other tab deleted", () => {
    const base = baseDocument();
    const edited = withPoints(base, "item_002", 7);
    const newest: NativeExamDocument = {
      ...base,
      items: base.items.filter((item) => item.item_id !== "item_002"),
    };

    const merged = mergeKept(base, edited, newest);

    expect(itemById(merged, "item_002").points).toBe(7);
    assertValidDocument(merged);
  });

  it("uses the edited order when the edit reordered, appending newest-only items", () => {
    const base = baseDocument();
    const edited: NativeExamDocument = {
      ...base,
      items: [
        { ...base.items[1], sequence: 1 },
        { ...base.items[0], sequence: 2 },
      ],
    };
    const added: NativeExamItem = { ...newTeacherItem("item_003", 3, "free_text"), points: 4 };
    const newest: NativeExamDocument = { ...base, items: [...base.items, added] };

    const merged = mergeKept(base, edited, newest);

    expect(itemIds(merged)).toEqual(["item_002", "item_001", "item_003"]);
    assertValidDocument(merged);
  });

  it("keeps the newest order when the edit did not reorder", () => {
    const base = baseDocument();
    const edited = withPoints(base, "item_001", 7);
    const newest: NativeExamDocument = {
      ...base,
      items: [
        { ...base.items[1], sequence: 1 },
        { ...base.items[0], sequence: 2 },
      ],
    };

    const merged = mergeKept(base, edited, newest);

    expect(itemIds(merged)).toEqual(["item_002", "item_001"]);
    expect(itemById(merged, "item_001").points).toBe(7);
    assertValidDocument(merged);
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

    const merged = mergeKept(base, edited, newest);

    expect(merged.title).toBe("Min titel");
    expect(merged.header.course_hint).toBe("Matematik 1");
    expect(merged.revision).toBe(5);
    expect(merged.document_id).toBe(newest.document_id);
    expect(merged.origin).toEqual(newest.origin);
    expect(merged.schema_version).toBe(newest.schema_version);
    assertValidDocument(merged);
  });

  it("renumbers after a remote delete plus a local edit instead of keeping the stale sequence", () => {
    const base = baseDocument();
    const edited = withPoints(base, "item_002", 7);
    const newest: NativeExamDocument = {
      ...base,
      items: [{ ...itemById(base, "item_002"), sequence: 1 }],
    };

    const merged = mergeKept(base, edited, newest);

    expect(itemIds(merged)).toEqual(["item_002"]);
    expect(merged.items.map((item) => item.sequence)).toEqual([1]);
    expect(itemById(merged, "item_002").points).toBe(7);
    assertValidDocument(merged);
  });

  it("restores an edited question's asset declaration when the other tab deleted it", () => {
    const pictured = {
      ...newTeacherItem("item_002", 2, "free_text"),
      body: pictureBody("asset_001"),
      points: 2,
    };
    const base = documentWith([newTeacherItem("item_001", 1, "free_text"), pictured], {
      assets: [asset("asset_001")],
    });
    const edited = withPoints(base, "item_002", 7);
    const newest: NativeExamDocument = {
      ...base,
      assets: [],
      items: [itemById(base, "item_001")],
    };

    const merged = mergeKept(base, edited, newest);

    expect(itemById(merged, "item_002").points).toBe(7);
    expect(merged.assets.map((entry) => entry.asset_id)).toEqual(["asset_001"]);
    assertValidDocument(merged);
  });

  it("drops an asset declaration the merged content no longer references", () => {
    const pictured = {
      ...newTeacherItem("item_001", 1, "free_text"),
      body: pictureBody("asset_001"),
    };
    const base = documentWith([pictured, newTeacherItem("item_002", 2, "free_text")], {
      assets: [asset("asset_001")],
    });
    const edited: NativeExamDocument = {
      ...base,
      items: base.items.map((item) =>
        item.item_id === "item_001" ? { ...item, body: [] } : item,
      ),
    };
    const newest = withPoints(base, "item_002", 9);

    const merged = mergeKept(base, edited, newest);

    expect(merged.assets).toEqual([]);
    expect(itemById(merged, "item_001").body).toEqual([]);
    assertValidDocument(merged);
  });

  it("reconciles a parent instruction edit with a remote child delete", () => {
    const base = documentWith(
      [
        { ...newTeacherItem("item_001", 1, "free_text"), points: 2 },
        { ...newTeacherItem("item_002", 2, "free_text"), points: 2 },
      ],
      { parents: [parentOf("parent_001", ["item_001", "item_002"], 0, "Del A")] },
    );
    const edited: NativeExamDocument = {
      ...base,
      parents: [parentOf("parent_001", ["item_001", "item_002"], 0, "Del A ändrad")],
    };
    const newest: NativeExamDocument = {
      ...base,
      items: [{ ...itemById(base, "item_001"), sequence: 1 }],
      parents: [parentOf("parent_001", ["item_001"], 0, "Del A")],
    };

    const merged = mergeKept(base, edited, newest);

    expect(itemIds(merged)).toEqual(["item_001"]);
    expect(merged.parents.map((parent) => parent.item_ids)).toEqual([["item_001"]]);
    expect(merged.parents[0].instruction).toEqual(textInstruction("Del A ändrad"));
    assertValidDocument(merged);
  });

  it("lets the kept edit win whole when both tabs deleted a different question", () => {
    const base = baseDocument();
    const edited: NativeExamDocument = {
      ...base,
      items: [{ ...itemById(base, "item_002"), sequence: 1 }],
    };
    const newest: NativeExamDocument = {
      ...base,
      items: [{ ...itemById(base, "item_001"), sequence: 1 }],
    };

    const merged = mergeKept(base, edited, newest);

    expect(itemIds(merged)).toEqual(["item_002"]);
    expect(itemById(merged, "item_002").points).toBe(
      itemById(base, "item_002").points,
    );
    expect(merged.items.map((item) => item.sequence)).toEqual([1]);
    expect(merged.revision).toBe(newest.revision);
    expect(merged.document_id).toBe(newest.document_id);
    assertValidDocument(merged);
  });

  it("keeps equal-place childless blocks in order on an unrelated title edit", () => {
    const base = documentWith(
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
    const edited: NativeExamDocument = { ...base, title: "Kept title" };
    const newest: NativeExamDocument = { ...base, title: "Remote title" };

    const merged = mergeKept(base, edited, newest);

    expect(merged.parents.map((parent) => parent.parent_id)).toEqual([
      "parent_001",
      "parent_002",
    ]);
    assertValidDocument(merged);
  });

  it("places childless blocks at different question-relative positions", () => {
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
    const edited: NativeExamDocument = { ...base, title: "Kept title" };
    const newest: NativeExamDocument = { ...base, title: "Remote title" };

    const merged = mergeKept(base, edited, newest);

    expect(merged.parents.map((parent) => parent.parent_id)).toEqual([
      "parent_001",
      "parent_002",
    ]);
    expect(merged.parents.map((parent) => parent.place)).toEqual([0, 2]);
    assertValidDocument(merged);
  });

  it("filters header question tags to the surviving items", () => {
    const base = documentWith(
      [
        { ...newTeacherItem("item_001", 1, "free_text"), points: 2 },
        { ...newTeacherItem("item_002", 2, "free_text"), points: 2 },
      ],
      {
        header: {
          tags: [
            { id: "tag_1", origin: "teacher", question_ids: ["item_001", "item_002"], text: "Båda" },
          ],
        },
      },
    );
    const edited = withPoints(base, "item_001", 7);
    const newest: NativeExamDocument = {
      ...base,
      items: [{ ...itemById(base, "item_001"), sequence: 1 }],
    };

    const merged = mergeKept(base, edited, newest);

    expect(merged.header.tags.map((tag) => tag.question_ids)).toEqual([["item_001"]]);
    assertValidDocument(merged);
  });
});
