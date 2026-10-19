/**
 * Matching item fixture for exam workspace specs.
 *
 * Purpose:
 *   Build the native matching item of the real English corpus question
 *   "Vocabulary Matching, Question 1" (three definitions, three words, facit
 *   1→truancy, 2→incarceration, 3→disdain) so every spec attacks the same
 *   shape the converter produces.
 */

import type { NativeExamItem } from "../../../api/examWorkspace";

export function buildMatchingItem(overrides: Partial<NativeExamItem> = {}): NativeExamItem {
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
      match_pairs: [
        { left_id: "left_001", right_id: "right_002" },
        { left_id: "left_002", right_id: "right_001" },
        { left_id: "left_003", right_id: "right_003" },
      ],
      origin: "source_provided",
    },
    body: [{ heading_level: null, segments: [{ kind: "text", marks: [], text: "Match each definition with the right word." }] }],
    choices: [],
    gaps: [],
    item_id: "item_001",
    kind: "matching",
    match_left: [
      { body: [{ heading_level: null, segments: [{ kind: "text", marks: [], text: "absence from school without permission" }] }], left_id: "left_001" },
      { body: [{ heading_level: null, segments: [{ kind: "text", marks: [], text: "being kept in a prison or jail" }] }], left_id: "left_002" },
      { body: [{ heading_level: null, segments: [{ kind: "text", marks: [], text: "a feeling that someone deserves no respect" }] }], left_id: "left_003" },
    ],
    match_right: [
      { body: [{ heading_level: null, segments: [{ kind: "text", marks: [], text: "incarceration" }] }], right_id: "right_001" },
      { body: [{ heading_level: null, segments: [{ kind: "text", marks: [], text: "truancy" }] }], right_id: "right_002" },
      { body: [{ heading_level: null, segments: [{ kind: "text", marks: [], text: "disdain" }] }], right_id: "right_003" },
    ],
    points: 3,
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
    tick_points: "1",
    writing_lines: null,
    ...overrides,
  };
}

/** The same item with its key replaced by the given `[left, right]` index pairs (1-based). */
export function buildMatchingItemWithPairs(
  pairs: Array<[number, number]>,
  overrides: Partial<NativeExamItem> = {},
): NativeExamItem {
  const base = buildMatchingItem();
  return buildMatchingItem({
    answer_key: {
      ...base.answer_key,
      match_pairs: pairs.map(([left, right]) => ({
        left_id: `left_00${left}`,
        right_id: `right_00${right}`,
      })),
    },
    ...overrides,
  });
}

/**
 * The same item with a fourth right entry that belongs to no left entry,
 * "ferocious" from the corpus question that follows it, keyed with the corpus pairs.
 */
export function buildMatchingItemWithDistractor(
  overrides: Partial<NativeExamItem> = {},
): NativeExamItem {
  const base = buildMatchingItem();
  return buildMatchingItem({
    match_right: [...base.match_right, { body: [{ heading_level: null, segments: [{ kind: "text", marks: [], text: "ferocious" }] }], right_id: "right_004" }],
    ...overrides,
  });
}
