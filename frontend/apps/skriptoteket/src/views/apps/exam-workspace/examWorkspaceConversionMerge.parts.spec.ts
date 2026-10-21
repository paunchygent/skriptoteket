/**
 * Conversion merge rebuilds part membership as members, never a place (F1, R1).
 *
 * Expected behavior:
 *   A converting question the head delivers as several items stays inside its
 *   part in the first item's slot, with the teacher's edited part instruction
 *   kept, whether that child was earlier in the part or the last child. A
 *   childless block keeps its index among the units, so its place follows the
 *   number of items before it once an earlier expansion landed, and a run of
 *   adjacent childless blocks keeps the head's delivered order. Every result is
 *   a valid outline: the structure owner's round trip is the identity and each
 *   part's children are consecutive in the merged items.
 */

import { describe, expect, it } from "vitest";

import type {
  ExamWorkspaceConversionUnit,
  NativeExamBodyParagraph,
  NativeExamDocument,
  NativeExamItem,
  NativeExamParent,
} from "../../../api/examWorkspace";
import { mergeConversionRevision } from "./examWorkspaceConversionMerge";
import { examWorkspaceUnits, withUnits } from "./examWorkspaceStructure";

function item(itemId: string, text: string, sequence = 0): NativeExamItem {
  return {
    ai_suggestion: null,
    writing_lines: null,
    leftover_points_text: null,
    answer_key: { correct_choice_ids: [], match_pairs: [], origin: "not_applicable" },
    body: [{ heading_level: null, segments: [{ kind: "text", marks: [], text }] }],
    choices: [],
    criteria: [],
    facit_text: null,
    gaps: [],
    kept_gaps: [],
    import_record: null,
    item_id: itemId,
    kind: "free_text",
    match_left: [],
    match_right: [],
    points: 2,
    points_estimated: false,
    print_order: [],
    printed_label: null,
    retry_source: null,
    review: {
      confidence: 0.9,
      parse_origin: "deterministic",
      reasons: [],
      state: "review_complete",
    },
    sequence,
    source_anchor: null,
    source_points: null,
    conflicting_source_points: [],
    suggested_kind: null,
    tick_points: null,
  };
}

function instruction(text: string): NativeExamBodyParagraph[] {
  return [{ heading_level: null, segments: [{ kind: "text", marks: [], text }] }];
}

function part(parentId: string, place: number, itemIds: string[], text: string): NativeExamParent {
  return { instruction: instruction(text), item_ids: itemIds, parent_id: parentId, place };
}

function document(
  revision: number,
  items: NativeExamItem[],
  parents: NativeExamParent[],
): NativeExamDocument {
  return {
    assets: [],
    document_id: "00000000-0000-4000-8000-000000000001",
    header: { tags: [] },
    instructions: [],
    items: items.map((entry, index) => ({ ...entry, sequence: index + 1 })),
    origin: { kind: "docx_import" },
    parents,
    revision,
    schema_version: "native_exam_document_v11",
    title: "Prov",
  };
}

function unit(
  unitId: string,
  state: ExamWorkspaceConversionUnit["state"],
  itemIds: string[],
): ExamWorkspaceConversionUnit {
  return { item_ids: itemIds, question: true, state, unit_id: unitId };
}

/** The owner's round trip is the identity and every part's children are consecutive. */
function expectOwnerRoundTrip(merged: NativeExamDocument): void {
  expect(withUnits(merged, examWorkspaceUnits(merged))).toEqual(merged);
  for (const parent of merged.parents) {
    const positions = parent.item_ids.map((itemId) =>
      merged.items.findIndex((entry) => entry.item_id === itemId),
    );
    positions.forEach((at, offset) => {
      if (offset > 0) {
        expect(at).toBe(positions[offset - 1]! + 1);
      }
    });
  }
}

describe("conversion merge keeps a split question inside its part", () => {
  it("keeps an expanded first child in its part with the teacher's instruction (F1)", () => {
    const pending = item("item_001", "One pending");
    const second = item("item_002", "Two");
    const third = item("item_003", "Three");
    const base = document(
      1,
      [pending, second, third],
      [part("parent_001", 0, ["item_001", "item_002"], "Välj rätt svar.")],
    );
    const local = document(
      1,
      [pending, second, third],
      [part("parent_001", 0, ["item_001", "item_002"], "Teacher edited instruction")],
    );
    const head = document(
      2,
      [item("item_001", "One"), item("item_1001", "One extra"), second, third],
      [part("parent_001", 0, ["item_001", "item_1001", "item_002"], "Välj rätt svar.")],
    );
    const baseUnits = [
      unit("q1", "converting", ["item_001"]),
      unit("q2", "ready", ["item_002"]),
      unit("q3", "ready", ["item_003"]),
    ];
    const headUnits = [
      unit("q1", "ready", ["item_001", "item_1001"]),
      unit("q2", "ready", ["item_002"]),
      unit("q3", "ready", ["item_003"]),
    ];

    const merged = mergeConversionRevision({ base, baseUnits, head, headUnits, local });

    expect(merged.items.map((entry) => entry.item_id)).toEqual([
      "item_001",
      "item_1001",
      "item_002",
      "item_003",
    ]);
    expect(merged.items.map((entry) => entry.sequence)).toEqual([1, 2, 3, 4]);
    expect(merged.parents).toHaveLength(1);
    expect(merged.parents[0]!.parent_id).toBe("parent_001");
    expect(merged.parents[0]!.item_ids).toEqual(["item_001", "item_1001", "item_002"]);
    expect(merged.parents[0]!.instruction).toEqual(instruction("Teacher edited instruction"));
    expect(merged.parents[0]!.place).toBe(0);
    expectOwnerRoundTrip(merged);
  });

  it("keeps an expanded final child inside its part with the teacher's instruction (F1)", () => {
    const first = item("item_001", "One");
    const pending = item("item_002", "Two pending");
    const third = item("item_003", "Three");
    const base = document(
      1,
      [first, pending, third],
      [part("parent_001", 0, ["item_001", "item_002"], "Välj rätt svar.")],
    );
    const local = document(
      1,
      [first, pending, third],
      [part("parent_001", 0, ["item_001", "item_002"], "Teacher edited instruction")],
    );
    const head = document(
      2,
      [first, item("item_002", "Two"), item("item_1002", "Two extra"), third],
      [part("parent_001", 0, ["item_001", "item_002", "item_1002"], "Välj rätt svar.")],
    );
    const baseUnits = [
      unit("q1", "ready", ["item_001"]),
      unit("q2", "converting", ["item_002"]),
      unit("q3", "ready", ["item_003"]),
    ];
    const headUnits = [
      unit("q1", "ready", ["item_001"]),
      unit("q2", "ready", ["item_002", "item_1002"]),
      unit("q3", "ready", ["item_003"]),
    ];

    const merged = mergeConversionRevision({ base, baseUnits, head, headUnits, local });

    expect(merged.items.map((entry) => entry.item_id)).toEqual([
      "item_001",
      "item_002",
      "item_1002",
      "item_003",
    ]);
    expect(merged.parents).toHaveLength(1);
    expect(merged.parents[0]!.item_ids).toEqual(["item_001", "item_002", "item_1002"]);
    expect(merged.parents[0]!.instruction).toEqual(instruction("Teacher edited instruction"));
    expect(merged.parents[0]!.place).toBe(0);
    expectOwnerRoundTrip(merged);
  });

  it("keeps a childless block's index and moves its place past an earlier expansion", () => {
    const pending = item("item_001", "One pending");
    const second = item("item_002", "Two");
    const third = item("item_003", "Three");
    const base = document(
      1,
      [pending, second, third],
      [part("parent_009", 2, [], "Mellanrubrik")],
    );
    const local = document(
      1,
      [pending, second, third],
      [part("parent_009", 2, [], "Teacher edited block")],
    );
    const head = document(
      2,
      [item("item_001", "One"), item("item_1001", "One extra"), second, third],
      [part("parent_009", 3, [], "Mellanrubrik")],
    );
    const baseUnits = [
      unit("q1", "converting", ["item_001"]),
      unit("q2", "ready", ["item_002"]),
      unit("q3", "ready", ["item_003"]),
    ];
    const headUnits = [
      unit("q1", "ready", ["item_001", "item_1001"]),
      unit("q2", "ready", ["item_002"]),
      unit("q3", "ready", ["item_003"]),
    ];

    const merged = mergeConversionRevision({ base, baseUnits, head, headUnits, local });

    expect(merged.items.map((entry) => entry.item_id)).toEqual([
      "item_001",
      "item_1001",
      "item_002",
      "item_003",
    ]);
    expect(merged.parents).toHaveLength(1);
    expect(merged.parents[0]!.parent_id).toBe("parent_009");
    expect(merged.parents[0]!.item_ids).toEqual([]);
    expect(merged.parents[0]!.instruction).toEqual(instruction("Teacher edited block"));
    expect(merged.parents[0]!.place).toBe(3);
    expectOwnerRoundTrip(merged);
  });
});

describe("conversion merge keeps delivered adjacent instruction blocks in order (F9)", () => {
  const first = item("item_001", "One");
  const second = item("item_002", "Two");
  const third = item("item_003", "Three");
  const units = [
    unit("q1", "ready", ["item_001"]),
    unit("q2", "ready", ["item_002"]),
    unit("q3", "ready", ["item_003"]),
  ];

  function headWith(place: number): NativeExamDocument {
    return document(2, [first, second, third], [
      part("parent_001", place, [], "First instruction"),
      part("parent_002", place, [], "Second instruction"),
    ]);
  }

  function merge(
    place: number,
    localTitle: string,
  ): { head: NativeExamDocument; merged: NativeExamDocument } {
    const base = document(1, [first, second, third], []);
    const local = { ...document(1, [first, second, third], []), title: localTitle };
    const head = headWith(place);
    const merged = mergeConversionRevision({ base, baseUnits: units, head, headUnits: units, local });
    return { head, merged };
  }

  function unitIds(document: NativeExamDocument): string[] {
    return examWorkspaceUnits(document).map((unit) =>
      unit.kind === "item" ? unit.itemId : unit.parentId,
    );
  }

  function expectHeadBlocks(
    merged: NativeExamDocument,
    head: NativeExamDocument,
    place: number,
  ): void {
    expect(examWorkspaceUnits(merged)).toEqual(examWorkspaceUnits(head));
    expect(merged.items.map((entry) => entry.item_id)).toEqual([
      "item_001",
      "item_002",
      "item_003",
    ]);
    expect(merged.parents.map((parent) => parent.parent_id)).toEqual([
      "parent_001",
      "parent_002",
    ]);
    expect(merged.parents.map((parent) => parent.place)).toEqual([place, place]);
    expect(merged.parents.map((parent) => parent.instruction)).toEqual([
      instruction("First instruction"),
      instruction("Second instruction"),
    ]);
    expectOwnerRoundTrip(merged);
  }

  it("keeps a leading run in head order when the copy is clean", () => {
    const { head, merged } = merge(0, "Prov");
    expectHeadBlocks(merged, head, 0);
    expect(unitIds(merged)).toEqual([
      "parent_001",
      "parent_002",
      "item_001",
      "item_002",
      "item_003",
    ]);
  });

  it("keeps a leading run in head order under a dirty local title", () => {
    const { head, merged } = merge(0, "Lokal rubrik");
    expectHeadBlocks(merged, head, 0);
    expect(unitIds(merged)).toEqual([
      "parent_001",
      "parent_002",
      "item_001",
      "item_002",
      "item_003",
    ]);
    expect(merged.title).toBe("Lokal rubrik");
  });

  it("keeps a middle run in head order when the copy is clean", () => {
    const { head, merged } = merge(1, "Prov");
    expectHeadBlocks(merged, head, 1);
    expect(unitIds(merged)).toEqual([
      "item_001",
      "parent_001",
      "parent_002",
      "item_002",
      "item_003",
    ]);
  });

  it("keeps a middle run in head order under a dirty local title", () => {
    const { head, merged } = merge(1, "Lokal rubrik");
    expectHeadBlocks(merged, head, 1);
    expect(unitIds(merged)).toEqual([
      "item_001",
      "parent_001",
      "parent_002",
      "item_002",
      "item_003",
    ]);
    expect(merged.title).toBe("Lokal rubrik");
  });

  it("keeps a trailing run in head order when the copy is clean", () => {
    const { head, merged } = merge(3, "Prov");
    expectHeadBlocks(merged, head, 3);
    expect(unitIds(merged)).toEqual([
      "item_001",
      "item_002",
      "item_003",
      "parent_001",
      "parent_002",
    ]);
  });

  it("keeps a trailing run in head order under a dirty local title", () => {
    const { head, merged } = merge(3, "Lokal rubrik");
    expectHeadBlocks(merged, head, 3);
    expect(unitIds(merged)).toEqual([
      "item_001",
      "item_002",
      "item_003",
      "parent_001",
      "parent_002",
    ]);
    expect(merged.title).toBe("Lokal rubrik");
  });
});
