/**
 * Fritext criteria on the item edit helpers (TASK-SKRIPT-39-09-04, Q12).
 *
 * Expected behavior:
 *   Replacing the criteria list with a non-empty list makes the item's points
 *   the exact sum of the criterion points and stops treating them as an
 *   estimate from a printed section total; an empty list leaves the item's
 *   points alone. A new teacher item starts with no criteria.
 */

import { describe, expect, it } from "vitest";

import type { NativeExamItem } from "../../../api/examWorkspace";
import { newTeacherItem, withCriteria, withPoints } from "./examWorkspaceItemEdits";
import { plainBody } from "./examWorkspaceRichText";

function buildFreeTextItem(overrides: Partial<NativeExamItem> = {}): NativeExamItem {
  return {
    ai_suggestion: null,
    facit_text: null,
    import_record: null,
    criteria: [],
    printed_label: null,
    print_order: [],
    retry_source: null,
    answer_key: { correct_choice_ids: [], match_pairs: [], origin: "not_applicable" },
    body: [{ heading_level: null, segments: [{ kind: "text", marks: [], text: "Förklara begreppet." }] }],
    choices: [],
    gaps: [],
    kept_gaps: [],
    item_id: "item_001",
    kind: "free_text",
    match_left: [],
    match_right: [],
    points: null,
    points_estimated: false,
    review: {
      confidence: null,
      parse_origin: "teacher_created",
      reasons: [],
      state: "review_complete",
    },
    sequence: 1,
    source_anchor: null,
    source_points: null,
    conflicting_source_points: [],
    suggested_kind: null,
    tick_points: null,
    writing_lines: 8,
    leftover_points_text: null,
    ...overrides,
  };
}

describe("withCriteria", () => {
  it("makes the item's points the exact sum of the criterion points", () => {
    const item = withCriteria(buildFreeTextItem(), [
      { points: 2, text: "Definition" },
      { points: 1, text: "Exempel" },
    ]);

    expect(item.criteria).toEqual([
      { points: 2, text: "Definition" },
      { points: 1, text: "Exempel" },
    ]);
    expect(item.points).toBe(3);
  });

  it("stops treating the points as an estimate from a printed total", () => {
    const item = withCriteria(buildFreeTextItem({ points: 3, points_estimated: true }), [
      { points: 3, text: "Hela svaret" },
    ]);

    expect(item.points).toBe(3);
    expect(item.points_estimated).toBe(false);
  });

  it("keeps the item's points when the list is cleared", () => {
    const item = withCriteria(buildFreeTextItem({ points: 2 }), []);

    expect(item.criteria).toEqual([]);
    expect(item.points).toBe(2);
  });
});

describe("newTeacherItem", () => {
  it("starts a new free-text question with no criteria", () => {
    expect(newTeacherItem("item_009", 9, "free_text").criteria).toEqual([]);
  });

  it("carries no printed source value on teacher items but keeps it through teacher edits", () => {
    expect(newTeacherItem("item_009", 9, "free_text").source_points).toBeNull();

    const imported = buildFreeTextItem({ points: 2, source_points: 7 });
    expect(withPoints(imported, 5).source_points).toBe(7);
    expect(
      withCriteria(imported, [{ points: 5, text: "Hela svaret" }]).source_points,
    ).toBe(7);
  });
});

describe("kept-answers wire format (TASK-SKRIPT-40-04-13 T1)", () => {
  it("carries no kept gaps on a fresh fixture item", () => {
    expect(buildFreeTextItem().kept_gaps).toEqual([]);
  });

  it("carries no kept gaps on a new teacher item of every kind", () => {
    for (const teacherKind of [
      "free_text",
      "single_choice",
      "multiple_response",
      "gap_fill",
      "inline_choice",
      "matching",
      "ordering",
      "short_answer",
    ] as const) {
      expect(newTeacherItem("item_009", 9, teacherKind).kept_gaps).toEqual([]);
    }
  });

  it("carries a null kept-gap link on a fresh plain-text segment", () => {
    expect(plainBody("Vilket ämne är en gas?")[0]!.segments[0]).toEqual({
      kept_gap_id: null,
      kind: "text",
      marks: [],
      text: "Vilket ämne är en gas?",
    });
  });
});
