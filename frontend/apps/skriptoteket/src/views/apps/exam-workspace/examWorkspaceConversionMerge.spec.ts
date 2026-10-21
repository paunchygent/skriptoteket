/**
 * Exam workspace conversion merge.
 *
 * Expected behavior:
 *   A unit that was still converting in the base (a placeholder) is always
 *   replaced by the items the server wrote, whatever the local copy holds for
 *   it: in place, or after the nearest preceding unit when the local copy
 *   lacks it. A converted unit the teacher has not touched since the base is
 *   replaced the same way; a converted unit the teacher edited keeps the
 *   teacher's version. Items the teacher added keep their place and get a
 *   fresh id when a converted item claims theirs. Title, instructions and
 *   parents follow the converted-unit rule. The result carries the head's
 *   revision and reports whether the document differs from the head.
 */

import { describe, expect, it } from "vitest";

import type {
  ExamWorkspaceConversionUnit,
  NativeExamBodyParagraph,
  NativeExamDocument,
  NativeExamItem,
} from "../../../api/examWorkspace";
import { mergeConversionRevision, sameDocument } from "./examWorkspaceConversionMerge";

function buildItem(itemId: string, text: string): NativeExamItem {
  return {
    ai_suggestion: null,
    facit_text: null,
    import_record: null,
    criteria: [],
    printed_label: null,
    print_order: [],
    retry_source: null,
    answer_key: {
      correct_choice_ids: [],
      match_pairs: [],
      origin: "not_applicable",
    },
    body: [{ heading_level: null, segments: [{ kind: "text", marks: [], text }] }],
    choices: [],
    gaps: [],
    kept_gaps: [],
    item_id: itemId,
    kind: "free_text",
    match_left: [],
    match_right: [],
    points: 2,
    points_estimated: false,
    review: {
      confidence: 0.9,
      parse_origin: "deterministic",
      reasons: [],
      state: "review_complete",
    },
    sequence: 0,
    source_anchor: null,
    source_points: null,
    conflicting_source_points: [],
    suggested_kind: null,
    tick_points: null,
    writing_lines: 8,
    leftover_points_text: null,
  };
}

function paragraph(text: string): NativeExamBodyParagraph {
  return { heading_level: null, segments: [{ kind: "text", marks: [], text }] };
}

function buildDocument(
  revision: number,
  items: NativeExamItem[],
  overrides: Partial<NativeExamDocument> = {},
): NativeExamDocument {
  return {
    assets: [],
    document_id: "00000000-0000-4000-8000-000000000001",
    instructions: [paragraph("Svara på alla frågor.")],
    items: items.map((item, index) => ({ ...item, sequence: index + 1 })),
    origin: { kind: "docx_import" },
    parents: [],
    revision,
    header: { tags: [] },
    schema_version: "native_exam_document_v11",
    title: "Prov",
    ...overrides,
  };
}

function unit(
  unitId: string,
  state: ExamWorkspaceConversionUnit["state"],
  itemIds: string[],
): ExamWorkspaceConversionUnit {
  return { item_ids: itemIds, question: true, state, unit_id: unitId };
}

const placeholder = buildItem("item_002", "Konverteras …");
const baseItems = [
  buildItem("item_001", "Fråga 1"),
  placeholder,
  buildItem("item_003", "Fråga 3"),
];
const baseUnits = [
  unit("q1", "ready", ["item_001"]),
  unit("q2", "converting", ["item_002"]),
  unit("q3", "ready", ["item_003"]),
];
const convertedItems = [
  buildItem("item_002", "Fråga 2a"),
  buildItem("item_004", "Fråga 2b"),
];
const headUnits = [
  unit("q1", "ready", ["item_001"]),
  unit("q2", "ready", ["item_002", "item_004"]),
  unit("q3", "ready", ["item_003"]),
];

const base = buildDocument(1, baseItems);
const head = buildDocument(2, [
  baseItems[0]!,
  ...convertedItems,
  baseItems[2]!,
]);

function textOf(item: NativeExamItem): string {
  const segment = item.body[0]!.segments[0]!;
  return segment.kind === "text" ? segment.text : "";
}

describe("mergeConversionRevision", () => {
  it("replaces an untouched placeholder by the converted items in place", () => {
    const document = mergeConversionRevision({
      base,
      baseUnits,
      head,
      headUnits,
      local: base,
    });

    expect(document.items.map((item) => item.item_id)).toEqual([
      "item_001",
      "item_002",
      "item_004",
      "item_003",
    ]);
    expect(document.items.map(textOf)).toEqual([
      "Fråga 1",
      "Fråga 2a",
      "Fråga 2b",
      "Fråga 3",
    ]);
    expect(document.items.map((item) => item.sequence)).toEqual([1, 2, 3, 4]);
    expect(document.revision).toBe(2);
    expect(sameDocument(document, head)).toBe(true);
    expect(document).toEqual(head);
  });

  it("replaces a placeholder whose local copy differs from the base by the converted items", () => {
    const changed = buildItem("item_002", "Lärarens egen text");
    const local = buildDocument(1, [baseItems[0]!, changed, baseItems[2]!]);

    const document = mergeConversionRevision({
      base,
      baseUnits,
      head,
      headUnits,
      local,
    });

    expect(document.items.map(textOf)).toEqual([
      "Fråga 1",
      "Fråga 2a",
      "Fråga 2b",
      "Fråga 3",
    ]);
    expect(document.revision).toBe(2);
    expect(sameDocument(document, head)).toBe(true);
    expect(document).toEqual(head);
  });

  it("inserts the converted items of a placeholder missing from the local copy in its place", () => {
    const local = buildDocument(1, [baseItems[0]!, baseItems[2]!]);

    const document = mergeConversionRevision({
      base,
      baseUnits,
      head,
      headUnits,
      local,
    });

    expect(document.items.map((item) => item.item_id)).toEqual([
      "item_001",
      "item_002",
      "item_004",
      "item_003",
    ]);
    expect(document.items.map(textOf)).toEqual([
      "Fråga 1",
      "Fråga 2a",
      "Fråga 2b",
      "Fråga 3",
    ]);
    expect(sameDocument(document, head)).toBe(true);
  });

  it("replaces only the placeholder and keeps the teacher's edit of a converted unit the server left alone", () => {
    const changed = buildItem("item_002", "Lärarens egen text");
    const edited = buildItem("item_001", "Lärarens ändring av fråga 1");
    const local = buildDocument(1, [edited, changed, baseItems[2]!]);

    const document = mergeConversionRevision({
      base,
      baseUnits,
      head,
      headUnits,
      local,
    });

    expect(document.items.map(textOf)).toEqual([
      "Lärarens ändring av fråga 1",
      "Fråga 2a",
      "Fråga 2b",
      "Fråga 3",
    ]);
    expect(sameDocument(document, head)).toBe(false);
  });

  it("renames a teacher-added item whose id a converted item claims, including its parent", () => {
    const added = buildItem("item_004", "Lärarens tillägg");
    const local = buildDocument(1, [...baseItems, added], {
      parents: [
        {
          instruction: [paragraph("Gemensam text")],
          item_ids: ["item_003", "item_004"],
          parent_id: "parent_001",
          place: 2,
        },
      ],
    });

    const document = mergeConversionRevision({
      base,
      baseUnits,
      head,
      headUnits,
      local,
    });

    const ids = document.items.map((item) => item.item_id);
    expect(ids).toEqual([
      "item_001",
      "item_002",
      "item_004",
      "item_003",
      "item_005",
    ]);
    expect(new Set(ids).size).toBe(ids.length);
    expect(textOf(document.items[2]!)).toBe("Fråga 2b");
    expect(textOf(document.items[4]!)).toBe("Lärarens tillägg");
    expect(document.parents[0]!.item_ids).toEqual(["item_003", "item_005"]);
  });

  it("keeps the teacher's edit of another unit while replacing the untouched unit", () => {
    const edited = buildItem("item_003", "Lärarens ändring av fråga 3");
    const local = buildDocument(1, [baseItems[0]!, placeholder, edited]);

    const document = mergeConversionRevision({
      base,
      baseUnits,
      head,
      headUnits,
      local,
    });

    expect(document.items.map(textOf)).toEqual([
      "Fråga 1",
      "Fråga 2a",
      "Fråga 2b",
      "Lärarens ändring av fråga 3",
    ]);
    expect(sameDocument(document, head)).toBe(false);
  });

  it("keeps the teacher's edit of a converted unit the server changed meanwhile", () => {
    const serverChangedQ3 = buildDocument(2, [
      baseItems[0]!,
      ...convertedItems,
      buildItem("item_003", "Fråga 3, omkonverterad"),
    ]);
    const edited = buildItem("item_003", "Lärarens ändring av fråga 3");
    const local = buildDocument(1, [baseItems[0]!, placeholder, edited]);

    const document = mergeConversionRevision({
      base,
      baseUnits,
      head: serverChangedQ3,
      headUnits,
      local,
    });

    expect(document.items.map(textOf)).toEqual([
      "Fråga 1",
      "Fråga 2a",
      "Fråga 2b",
      "Lärarens ändring av fråga 3",
    ]);
  });

  it("inserts a new unit after the nearest preceding unit with local items", () => {
    const newMiddle = buildItem("item_005", "Ny mellanfråga");
    const newLast = buildItem("item_006", "Ny sistafråga");
    const newUnitsHead = buildDocument(2, [
      baseItems[0]!,
      newMiddle,
      placeholder,
      baseItems[2]!,
      newLast,
    ]);
    const units = [
      unit("q1", "ready", ["item_001"]),
      unit("qx", "ready", ["item_005"]),
      unit("q2", "converting", ["item_002"]),
      unit("q3", "ready", ["item_003"]),
      unit("qy", "ready", ["item_006"]),
    ];
    const local = buildDocument(1, [baseItems[0]!, placeholder, baseItems[2]!]);

    const document = mergeConversionRevision({
      base,
      baseUnits,
      head: newUnitsHead,
      headUnits: units,
      local,
    });

    expect(document.items.map(textOf)).toEqual([
      "Fråga 1",
      "Ny mellanfråga",
      "Konverteras …",
      "Fråga 3",
      "Ny sistafråga",
    ]);
    expect(document.items.map((item) => item.sequence)).toEqual([
      1, 2, 3, 4, 5,
    ]);
    expect(sameDocument(document, newUnitsHead)).toBe(true);
  });

  it("inserts a new first unit at the start when no preceding unit has local items", () => {
    const first = buildItem("item_005", "Ny första");
    const firstHead = buildDocument(2, [first, ...baseItems]);
    const units = [unit("q0", "ready", ["item_005"]), ...baseUnits];

    const document = mergeConversionRevision({
      base,
      baseUnits,
      head: firstHead,
      headUnits: units,
      local: base,
    });

    expect(document.items.map(textOf)).toEqual([
      "Ny första",
      "Fråga 1",
      "Konverteras …",
      "Fråga 3",
    ]);
  });

  it("keeps the teacher's title while the head's title changed", () => {
    const retitled = { ...head, title: "Serverns titel" };
    const local = buildDocument(1, baseItems, { title: "Lärarens titel" });

    const document = mergeConversionRevision({
      base,
      baseUnits,
      head: retitled,
      headUnits,
      local,
    });

    expect(document.title).toBe("Lärarens titel");
    expect(sameDocument(document, retitled)).toBe(false);
  });

  it("takes the head's title and instructions when the teacher left them, and prunes parents", () => {
    const withParent = buildDocument(1, baseItems, {
      parents: [
        {
          instruction: [paragraph("Gemensam")],
          item_ids: ["item_001", "item_002"],
          parent_id: "parent_001",
          place: 0,
        },
      ],
    });
    const changedHead = buildDocument(
      2,
      [baseItems[0]!, ...convertedItems, baseItems[2]!],
      {
        instructions: [paragraph("Nya anvisningar.")],
        parents: [
          {
            instruction: [paragraph("Gemensam")],
            item_ids: ["item_002", "item_004"],
            parent_id: "parent_001",
            place: 1,
          },
          {
            instruction: [paragraph("Borta")],
            item_ids: ["item_099"],
            parent_id: "parent_002",
            place: 4,
          },
        ],
        title: "Serverns titel",
      },
    );
    const copy = { ...withParent, parents: base.parents };

    const document = mergeConversionRevision({
      base,
      baseUnits,
      head: changedHead,
      headUnits,
      local: copy,
    });

    expect(document.title).toBe("Serverns titel");
    expect(document.instructions).toEqual([paragraph("Nya anvisningar.")]);
    expect(document.parents.map((parent) => parent.item_ids)).toEqual([
      ["item_002", "item_004"],
    ]);
  });
  it("keeps what a later save from another tab added or changed among the teacher's own items", () => {
    const converted = buildItem("item_001", "Fråga ett");
    const teacherOwn = buildItem("item_003", "Lärarens fråga");
    const base = buildDocument(1, [converted, placeholder, teacherOwn]);
    const baseUnits = [unit("q1", "ready", ["item_001"]), unit("q2", "converting", ["item_002"])];
    const local = buildDocument(1, [{ ...converted, points: 7 }, placeholder, teacherOwn]);
    const otherTabAdded = buildItem("item_004", "Andra flikens fråga");
    const head = buildDocument(3, [
      converted,
      buildItem("item_002", "Fråga två"),
      { ...teacherOwn, points: 9 },
      otherTabAdded,
    ]);
    const headUnits = [unit("q1", "ready", ["item_001"]), unit("q2", "ready", ["item_002"])];

    const document = mergeConversionRevision({ base, baseUnits, head, headUnits, local });

    expect(document.items.map((item) => [item.item_id, item.points, item.body[0]?.segments[0]])).toEqual([
      ["item_001", 7, { kind: "text", marks: [], text: "Fråga ett" }],
      ["item_002", 2, { kind: "text", marks: [], text: "Fråga två" }],
      ["item_003", 9, { kind: "text", marks: [], text: "Lärarens fråga" }],
      ["item_004", 2, { kind: "text", marks: [], text: "Andra flikens fråga" }],
    ]);
    expect(document.revision).toBe(3);
  });

  it("keeps a childless part between two kept questions at its place through the merge", () => {
    const block = {
      instruction: [paragraph("Mellanrubrik")],
      item_ids: [] as string[],
      parent_id: "parent_001",
      place: 2,
    };
    const first = buildDocument(1, [buildItem("item_001", "Fråga 1"), buildItem("item_002", "Fråga 2"), buildItem("item_003", "Fråga 3")], {
      parents: [block],
    });
    const head = buildDocument(2, [buildItem("item_001", "Fråga 1 ny"), buildItem("item_002", "Fråga 2"), buildItem("item_003", "Fråga 3")], {
      parents: [block],
    });

    const document = mergeConversionRevision({
      base: first,
      baseUnits: [],
      head,
      headUnits: [],
      local: first,
    });

    expect(document.items.map(textOf)).toEqual(["Fråga 1 ny", "Fråga 2", "Fråga 3"]);
    expect(document.parents).toEqual([
      { instruction: [paragraph("Mellanrubrik")], item_ids: [], parent_id: "parent_001", place: 2 },
    ]);
  });
});
