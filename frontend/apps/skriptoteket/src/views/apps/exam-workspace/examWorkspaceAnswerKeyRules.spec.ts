/**
 * Exam workspace answer-key completeness rules.
 *
 * Expected behavior:
 *   A gap item is partially keyed only while its answer key is keyed and at
 *   least one gap has no accepted values. The refusal copy names one item in
 *   the singular and several items in the plural with a Swedish list joiner.
 *   A matching item is incomplete while its key is keyed and any left entry
 *   is missing from the pairs, any left or right entry is used more than once,
 *   or a pair names an unknown entry. A right entry in no pair is a distractor
 *   and keeps the key complete; an absent key with no pairs is never incomplete.
 */

import { describe, expect, it } from "vitest";

import type { NativeExamItem } from "../../../api/examWorkspace";
import {
  INCOMPLETE_MATCH_KEY_GUIDANCE,
  incompleteMatchKeyCopy,
  isIncompleteMatchingItem,
  isPartiallyKeyedGapItem,
  PARTIAL_GAP_KEY_GUIDANCE,
  partialGapKeyCopy,
} from "./examWorkspaceAnswerKeyRules";
import { buildGap } from "./examWorkspaceKeyedItems.specSupport";
import {
  buildMatchingItem,
  buildMatchingItemWithDistractor,
  buildMatchingItemWithPairs,
} from "./examWorkspaceMatchingItem.specSupport";

function buildGapItem(overrides: Partial<NativeExamItem> = {}): NativeExamItem {
  return {
    ai_suggestion: null,
    facit_text: null,
    import_record: null,
    criteria: [],
    printed_label: null,
    retry_source: null,
    answer_key: { correct_choice_ids: [], match_pairs: [], origin: "teacher_authored" },
    body: [
      { heading_level: null, segments: [
          { kind: "text", marks: [], text: "Vatten kokar vid" },
          { gap_id: "gap_001", kind: "gap" },
          { kind: "text", marks: [], text: "grader och fryser vid" },
          { gap_id: "gap_002", kind: "gap" },
          { kind: "text", marks: [], text: "grader." },
        ],
      },
    ],
    choices: [],
    gaps: [
      buildGap("gap_001", ["100"]),
      buildGap("gap_002"),
    ],
    item_id: "item_001",
    kind: "gap_fill",
    match_left: [],
    match_right: [],
    points: 1,
    points_estimated: false,
    review: {
      confidence: 0.95,
      parse_origin: "deterministic",
      reasons: [],
      state: "review_complete",
    },
    sequence: 1,
    source_anchor: null,
    suggested_kind: null,
    tick_points: null,
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
        buildGap("gap_001", ["100"]),
        buildGap("gap_002", ["0"]),
      ],
    });
    expect(isPartiallyKeyedGapItem(item)).toBe(false);
  });

  it("accepts a gap item whose answer key is absent", () => {
    const item = buildGapItem({ answer_key: { correct_choice_ids: [], match_pairs: [], origin: "absent" } });
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

describe("isIncompleteMatchingItem", () => {
  it("accepts the corpus key where every entry is paired once", () => {
    expect(isIncompleteMatchingItem(buildMatchingItem())).toBe(false);
  });

  it("rejects a keyed item that is missing one pair", () => {
    expect(
      isIncompleteMatchingItem(
        buildMatchingItemWithPairs([
          [1, 2],
          [2, 1],
        ]),
      ),
    ).toBe(true);
  });

  it("accepts one column serving several rows and a row with two ticks", () => {
    expect(
      isIncompleteMatchingItem(
        buildMatchingItemWithPairs([
          [1, 2],
          [2, 2],
          [2, 3],
          [3, 3],
        ]),
      ),
    ).toBe(false);
  });

  it("rejects a repeated tick", () => {
    expect(
      isIncompleteMatchingItem(
        buildMatchingItemWithPairs([
          [1, 2],
          [1, 2],
          [2, 1],
          [3, 3],
        ]),
      ),
    ).toBe(true);
  });

  it("accepts a keyed item with an unpaired right entry", () => {
    expect(isIncompleteMatchingItem(buildMatchingItemWithDistractor())).toBe(false);
  });

  it("accepts two rows ticking the same column beside an unused column", () => {
    expect(
      isIncompleteMatchingItem(
        buildMatchingItemWithDistractor({
          answer_key: {
            correct_choice_ids: [],
            match_pairs: [
              { left_id: "left_001", right_id: "right_004" },
              { left_id: "left_002", right_id: "right_004" },
              { left_id: "left_003", right_id: "right_003" },
            ],
            origin: "teacher_authored",
          },
        }),
      ),
    ).toBe(false);
  });

  it("rejects a distractor item that leaves a left entry unpaired", () => {
    const item = buildMatchingItemWithDistractor();

    expect(
      isIncompleteMatchingItem({
        ...item,
        answer_key: {
          ...item.answer_key,
          match_pairs: item.answer_key.match_pairs.slice(0, 2),
        },
      }),
    ).toBe(true);
  });

  it("rejects a keyed item whose pair names an unknown right entry", () => {
    expect(
      isIncompleteMatchingItem(
        buildMatchingItemWithPairs([
          [1, 2],
          [2, 1],
          [3, 9],
        ]),
      ),
    ).toBe(true);
  });

  it("rejects a keyed item with no pairs at all", () => {
    expect(isIncompleteMatchingItem(buildMatchingItemWithPairs([]))).toBe(true);
  });

  it("accepts an absent key with no pairs", () => {
    const item = buildMatchingItemWithPairs([]);

    expect(
      isIncompleteMatchingItem({ ...item, answer_key: { ...item.answer_key, origin: "absent" } }),
    ).toBe(false);
  });

  it("never flags a non-matching item", () => {
    expect(isIncompleteMatchingItem(buildGapItem())).toBe(false);
  });

  it("names the question and carries the guidance", () => {
    expect(incompleteMatchKeyCopy([buildMatchingItem({ sequence: 4 })])).toBe(
      `Fråga 4 har en kategorisering där facit inte är komplett. ${INCOMPLETE_MATCH_KEY_GUIDANCE}`,
    );
  });
});
