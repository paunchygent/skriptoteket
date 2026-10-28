/**
 * Exam workspace answer-key completeness rules.
 *
 * Expected behavior:
 *   A gap item is partially keyed only while its answer key is keyed and at
 *   least one gap has no accepted values. The refusal copy names one item in
 *   the singular and several items in the plural with a Swedish list joiner,
 *   using the question list's labels rather than the stored sequence.
 *   A matching item is incomplete while its key is keyed and any left entry
 *   is missing from the pairs, any left or right entry is used more than once,
 *   or a pair names an unknown entry. A right entry in no pair is a distractor
 *   and keeps the key complete; an absent key with no pairs is never incomplete.
 */

import { describe, expect, it } from "vitest";

import type { NativeExamDocument, NativeExamItem, NativeExamParent } from "../../../api/examWorkspace";
import {
  INCOMPLETE_MATCH_KEY_GUIDANCE,
  hasInvalidAnswerKey,
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

function examDocument(items: NativeExamItem[], parents: NativeExamParent[] = []): NativeExamDocument {
  return {
    assets: [],
    document_id: "00000000-0000-4000-8000-000000000001",
    header: { tags: [] },
    instructions: [],
    items,
    origin: { kind: "created" },
    parents,
    revision: 1,
    schema_version: "native_exam_document_v11",
    title: "Prov",
  };
}

function keyedGapItem(itemId: string, sequence: number): NativeExamItem {
  return buildGapItem({
    gaps: [
      buildGap("gap_001", ["100"]),
      buildGap("gap_002", ["0"]),
    ],
    item_id: itemId,
    sequence,
  });
}

function buildGapItem(overrides: Partial<NativeExamItem> = {}): NativeExamItem {
  return {
    ai_suggestion: null,
    answer_key_retry: "none",
    facit_text: null,
    import_record: null,
    criteria: [],
    printed_label: null,
    print_order: [],
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
    kept_gaps: [],
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
    source_points: null,
    conflicting_source_points: [],
    suggested_kind: null,
    tick_points: null,
    writing_lines: null,
    leftover_points_text: null,
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

describe("hasInvalidAnswerKey for empty gaps", () => {
  it("accepts a keyed gap_fill item with an empty gap as a valid draft", () => {
    expect(hasInvalidAnswerKey(buildGapItem())).toBe(false);
  });

  it("accepts a keyed dropdown item with a gap that has no correct option", () => {
    const item = buildGapItem({
      gaps: [buildGap("gap_001")],
      kind: "inline_choice",
    });

    expect(hasInvalidAnswerKey(item)).toBe(false);
  });

  it("still flags a keyed dropdown gap whose correct option names no declared option", () => {
    const item = buildGapItem({
      gaps: [buildGap("gap_001", [], { correct_option_id: "choice_009" })],
      kind: "inline_choice",
    });

    expect(hasInvalidAnswerKey(item)).toBe(true);
  });

  it("still flags a keyed gap_fill item that keys top-level choices", () => {
    const item = buildGapItem({
      answer_key: { correct_choice_ids: ["choice_001"], match_pairs: [], origin: "teacher_authored" },
      choices: [
        { body: [{ heading_level: null, segments: [{ kind: "text", marks: [], text: "Syre" }] }], choice_id: "choice_001" },
        { body: [{ heading_level: null, segments: [{ kind: "text", marks: [], text: "Järn" }] }], choice_id: "choice_002" },
      ],
    });
    expect(hasInvalidAnswerKey(item)).toBe(true);
  });
});

describe("partialGapKeyCopy", () => {
  it("names a single item by its list label, not its sequence", () => {
    const item = buildGapItem({ item_id: "item_001", sequence: 4 });
    const document = examDocument([item]);

    expect(partialGapKeyCopy(document, [item])).toBe(
      `Fråga 1 saknar godkända svar i vissa luckor. ${PARTIAL_GAP_KEY_GUIDANCE}`,
    );
  });

  it("joins several items with commas and och using their list labels", () => {
    const items = [3, 4, 7].map((sequence, index) =>
      buildGapItem({ item_id: `item_00${index + 1}`, sequence }),
    );
    const document = examDocument(items);

    expect(partialGapKeyCopy(document, items)).toBe(
      `Frågorna 1, 2 och 3 saknar godkända svar i vissa luckor. ${PARTIAL_GAP_KEY_GUIDANCE}`,
    );
  });

  it("names a question after a part of three children by its list label", () => {
    const children = [1, 2, 3].map((sequence) => keyedGapItem(`item_00${sequence}`, sequence));
    const refused = buildGapItem({ item_id: "item_004", sequence: 4 });
    const document = examDocument([...children, refused], [
      {
        instruction: [],
        item_ids: children.map((child) => child.item_id),
        parent_id: "parent_001",
        place: 0,
      },
    ]);

    expect(partialGapKeyCopy(document, [refused])).toBe(
      `Fråga 2 saknar godkända svar i vissa luckor. ${PARTIAL_GAP_KEY_GUIDANCE}`,
    );
    expect(partialGapKeyCopy(document, [refused])).not.toContain("Fråga 4");
  });

  it("names a refused child question with its letter", () => {
    const first = keyedGapItem("item_001", 1);
    const refused = buildGapItem({ item_id: "item_002", sequence: 2 });
    const document = examDocument([first, refused], [
      { instruction: [], item_ids: ["item_001", "item_002"], parent_id: "parent_001", place: 0 },
    ]);

    expect(partialGapKeyCopy(document, [refused])).toBe(
      `Fråga 1b saknar godkända svar i vissa luckor. ${PARTIAL_GAP_KEY_GUIDANCE}`,
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

  it("names the question by its list label and carries the guidance", () => {
    const item = buildMatchingItem({ item_id: "item_001", sequence: 4 });
    const document = examDocument([item]);

    expect(incompleteMatchKeyCopy(document, [item])).toBe(
      `Fråga 1 har en kategorisering där facit inte är komplett. ${INCOMPLETE_MATCH_KEY_GUIDANCE}`,
    );
  });
});
