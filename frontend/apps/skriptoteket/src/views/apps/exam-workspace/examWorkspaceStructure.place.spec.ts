/**
 * Parts read and write their stored place.
 *
 * Expected behavior:
 *   `examWorkspaceUnits` walks the items by index and emits every part at its
 *   stored place, including a part with no questions (an instruction block);
 *   `withUnits(document, examWorkspaceUnits(document))` is the identity, and
 *   the insert and delete transitions keep every part's place correct.
 */

import { describe, expect, it } from "vitest";

import type {
  NativeExamDocument,
  NativeExamItem,
  NativeExamParent,
} from "../../../api/examWorkspace";
import { newTeacherItem } from "./examWorkspaceItemEdits";
import {
  examWorkspaceMembers,
  examWorkspaceUnits,
  withItemAfterUnit,
  withMembers,
  withoutStandaloneItem,
  withUnits,
} from "./examWorkspaceStructure";
import type { ExamWorkspaceMember, ExamWorkspaceUnit } from "./examWorkspaceStructure";

function question(sequence: number): NativeExamItem {
  return newTeacherItem(`item_${String(sequence).padStart(3, "0")}`, sequence, "free_text");
}

function documentOf(items: NativeExamItem[], parents: NativeExamParent[]): NativeExamDocument {
  return {
    assets: [],
    document_id: "00000000-0000-4000-8000-000000000001",
    header: { tags: [] },
    instructions: [],
    items,
    origin: { kind: "created" },
    parents,
    revision: 1,
    schema_version: "native_exam_document_v10",
    title: "Prov",
  };
}

function block(parentId: string, place: number): NativeExamParent {
  return { instruction: [], item_ids: [], parent_id: parentId, place };
}

function part(parentId: string, place: number, itemIds: string[]): NativeExamParent {
  return { instruction: [], item_ids: itemIds, parent_id: parentId, place };
}

function unitKeys(units: ExamWorkspaceUnit[]): string[] {
  return units.map((unit) =>
    unit.kind === "item" ? `item:${unit.itemId}` : `parent:${unit.parentId}:${unit.itemIds.join(",")}`,
  );
}

describe("parts read by their stored place", () => {
  it("puts a childless part first at place 0", () => {
    const document = documentOf([question(1), question(2)], [block("parent_001", 0)]);

    expect(unitKeys(examWorkspaceUnits(document))).toEqual([
      "parent:parent_001:",
      "item:item_001",
      "item:item_002",
    ]);
    expect(withUnits(document, examWorkspaceUnits(document))).toEqual(document);
  });

  it("puts a childless part between two questions", () => {
    const document = documentOf(
      [question(1), question(2), question(3)],
      [block("parent_001", 1)],
    );

    expect(unitKeys(examWorkspaceUnits(document))).toEqual([
      "item:item_001",
      "parent:parent_001:",
      "item:item_002",
      "item:item_003",
    ]);
    expect(withUnits(document, examWorkspaceUnits(document))).toEqual(document);
  });

  it("puts a childless part at the end", () => {
    const document = documentOf([question(1), question(2)], [block("parent_001", 2)]);

    expect(unitKeys(examWorkspaceUnits(document))).toEqual([
      "item:item_001",
      "item:item_002",
      "parent:parent_001:",
    ]);
    expect(withUnits(document, examWorkspaceUnits(document))).toEqual(document);
  });

  it("keeps two childless parts at one place in parents order", () => {
    const document = documentOf(
      [question(1), question(2)],
      [block("parent_001", 1), block("parent_002", 1)],
    );

    expect(unitKeys(examWorkspaceUnits(document))).toEqual([
      "item:item_001",
      "parent:parent_001:",
      "parent:parent_002:",
      "item:item_002",
    ]);
    expect(withUnits(document, examWorkspaceUnits(document))).toEqual(document);
  });

  it("puts a childless part directly before a part with questions", () => {
    const document = documentOf(
      [question(1), question(2), question(3)],
      [block("parent_001", 1), part("parent_002", 1, ["item_002", "item_003"])],
    );

    expect(unitKeys(examWorkspaceUnits(document))).toEqual([
      "item:item_001",
      "parent:parent_001:",
      "parent:parent_002:item_002,item_003",
    ]);
    expect(withUnits(document, examWorkspaceUnits(document))).toEqual(document);
  });
});

describe("inserting a question around a childless part", () => {
  function withChildlessPart(): NativeExamDocument {
    return documentOf([question(1), question(2)], [block("parent_001", 1)]);
  }

  it("inserts after the childless part without moving its place", () => {
    const document = withChildlessPart();

    const next = withItemAfterUnit(document, question(3), 1);

    expect(next.items.map((item) => item.item_id)).toEqual(["item_001", "item_003", "item_002"]);
    expect(next.parents).toEqual([block("parent_001", 1)]);
  });

  it("inserts before the childless part and shifts its place by one", () => {
    const document = withChildlessPart();

    const next = withItemAfterUnit(document, question(3), 0);

    expect(next.items.map((item) => item.item_id)).toEqual(["item_001", "item_003", "item_002"]);
    expect(next.parents).toEqual([block("parent_001", 2)]);
  });
});

describe("deleting a standalone question before a childless part", () => {
  it("lowers the childless part's place by one", () => {
    const document = documentOf([question(1), question(2)], [block("parent_001", 1)]);

    const next = withoutStandaloneItem(document, "item_001");

    expect(next.items.map((item) => item.item_id)).toEqual(["item_002"]);
    expect(next.parents).toEqual([block("parent_001", 0)]);
  });
});

function memberKeys(members: ExamWorkspaceMember[]): string[] {
  return members.map((member) =>
    member.kind === "item"
      ? `item:${member.item.item_id}:${member.parentId ?? ""}`
      : `block:${member.parentId}`,
  );
}

describe("reading and writing the member list", () => {
  it("round trips a document through members (standalone, part with two children, block)", () => {
    const document = documentOf(
      [question(1), question(2), question(3), question(4)],
      [part("parent_001", 1, ["item_002", "item_003"]), block("parent_002", 3)],
    );

    expect(memberKeys(examWorkspaceMembers(document))).toEqual([
      "item:item_001:",
      "item:item_002:parent_001",
      "item:item_003:parent_001",
      "block:parent_002",
      "item:item_004:",
    ]);
    expect(withMembers(document, examWorkspaceMembers(document), document.parents)).toEqual(
      document,
    );
  });

  it("splits a part whose members reappear through a fresh parent copy with the same instruction", () => {
    const parent: NativeExamParent = {
      instruction: [
        { heading_level: null, segments: [{ kind: "text", marks: [], text: "Gemensam" }] },
      ],
      item_ids: ["item_001"],
      parent_id: "parent_001",
      place: 0,
    };
    const document = documentOf([question(1), question(2), question(3)], [parent]);
    const members: ExamWorkspaceMember[] = [
      { kind: "item", item: document.items[0]!, parentId: "parent_001" },
      { kind: "item", item: document.items[1]!, parentId: null },
      { kind: "item", item: document.items[2]!, parentId: "parent_001" },
    ];

    const next = withMembers(document, members, document.parents);

    expect(next.items.map((item) => item.item_id)).toEqual(["item_001", "item_002", "item_003"]);
    expect(
      next.parents.map((entry) => [entry.parent_id, entry.place, entry.item_ids]),
    ).toEqual([
      ["parent_001", 0, ["item_001"]],
      ["parent_002", 2, ["item_003"]],
    ]);
    expect(next.parents[1]!.instruction).toEqual(parent.instruction);
    expect(withUnits(next, examWorkspaceUnits(next))).toEqual(next);
  });
});
