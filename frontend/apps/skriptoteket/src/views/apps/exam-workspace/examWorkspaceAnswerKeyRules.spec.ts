/**
 * Exam workspace answer-key completeness rules.
 *
 * Expected behavior:
 *   A gap item is partially keyed only while its answer key is keyed and at
 *   least one gap has no accepted values. The refusal copy names one item in
 *   the singular and several items in the plural with a Swedish list joiner.
 */

import { describe, expect, it } from "vitest";

import type { NativeExamItem } from "../../../api/examWorkspace";
import {
  isPartiallyKeyedGapItem,
  PARTIAL_GAP_KEY_GUIDANCE,
  partialGapKeyCopy,
} from "./examWorkspaceAnswerKeyRules";

function buildGapItem(overrides: Partial<NativeExamItem> = {}): NativeExamItem {
  return {
    answer_key: { correct_choice_ids: [], origin: "teacher_authored" },
    body: [
      {
        segments: [
          { kind: "text", text: "Vatten kokar vid" },
          { gap_id: "gap_001", kind: "gap" },
          { kind: "text", text: "grader och fryser vid" },
          { gap_id: "gap_002", kind: "gap" },
          { kind: "text", text: "grader." },
        ],
      },
    ],
    choices: [],
    gaps: [
      { accepted_values: ["100"], gap_id: "gap_001", hint: null },
      { accepted_values: [], gap_id: "gap_002", hint: null },
    ],
    item_id: "item_001",
    kind: "gap_fill",
    points: 1,
    review: {
      confidence: 0.95,
      parse_origin: "deterministic",
      reasons: [],
      state: "review_complete",
    },
    sequence: 1,
    source_anchor: null,
    title: "Kokpunkt",
    ...overrides,
  };
}

describe("isPartiallyKeyedGapItem", () => {
  it("flags a keyed gap item with an empty gap", () => {
    expect(isPartiallyKeyedGapItem(buildGapItem())).toBe(true);
  });

  it("accepts a gap item keyed in every gap", () => {
    const item = buildGapItem({
      gaps: [
        { accepted_values: ["100"], gap_id: "gap_001", hint: null },
        { accepted_values: ["0"], gap_id: "gap_002", hint: null },
      ],
    });
    expect(isPartiallyKeyedGapItem(item)).toBe(false);
  });

  it("accepts a gap item whose answer key is absent", () => {
    const item = buildGapItem({ answer_key: { correct_choice_ids: [], origin: "absent" } });
    expect(isPartiallyKeyedGapItem(item)).toBe(false);
  });

  it("ignores items that are not gap items", () => {
    expect(isPartiallyKeyedGapItem(buildGapItem({ kind: "free_text" }))).toBe(false);
  });
});

describe("partialGapKeyCopy", () => {
  it("names a single item in the singular", () => {
    expect(partialGapKeyCopy([buildGapItem({ sequence: 4 })])).toBe(
      `Fråga 4 saknar godkända svar i vissa luckor. ${PARTIAL_GAP_KEY_GUIDANCE}`,
    );
  });

  it("joins several items with commas and och", () => {
    const items = [3, 4, 7].map((sequence) => buildGapItem({ sequence }));
    expect(partialGapKeyCopy(items)).toBe(
      `Frågorna 3, 4 och 7 saknar godkända svar i vissa luckor. ${PARTIAL_GAP_KEY_GUIDANCE}`,
    );
  });
});
