/**
 * An arriving suggestion that no longer fits its question never becomes the
 * key (TASK-SKRIPT-39-04-07 T5 as amended by P13).
 *
 * Expected behavior:
 *   The teacher can change a question's choices, match entries or gaps while
 *   its request runs. An arrival that would then not be a valid key for the
 *   question's current kind and ids is kept on the question as its
 *   suggestion, and the key, its origin and the review state stay, whatever
 *   the key's origin. An arrival naming the declared ids in another order
 *   still fits. Restoring a kept suggestion that does not fit leaves the
 *   question unchanged, as the server refuses it.
 *
 * Rows follow case space D in the retained design note
 * `evidence/implementation/TASK-SKRIPT-39-04-07/repair3/design.md`.
 */

import { describe, expect, it } from "vitest";

import type { NativeAnswerKeySuggestion, NativeExamItem } from "../../../api/examWorkspace";
import { withArrivingSuggestion, withRestoredSuggestion } from "./examWorkspaceItemEdits";
import {
  UNREVIEWED,
  choiceItem,
  gapItem,
  gapSuggestion,
  keyedSuggestion,
  pairs,
} from "./examWorkspaceKeyedItems.specSupport";
import { buildMatchingItem } from "./examWorkspaceMatchingItem.specSupport";

const ARRIVING_PAIRS: Array<[string, string]> = [
  ["left_001", "right_003"],
  ["left_002", "right_002"],
  ["left_003", "right_001"],
];
const ARRIVING_GAPS = gapSuggestion([
  ["gap_001", ["Bo"]],
  ["gap_002", ["Umeå"]],
]);

function keylessMatchingItem(
  leftIds: string[] = ["left_001", "left_002", "left_003"],
  rightIds: string[] = ["right_001", "right_002", "right_003"],
): NativeExamItem {
  return buildMatchingItem({
    ai_suggestion: null,
    answer_key: { correct_choice_ids: [], match_pairs: [], origin: "absent" },
    match_left: leftIds.map((left_id) => ({ left_id, text: left_id })),
    match_right: rightIds.map((right_id) => ({ right_id, text: right_id })),
    points: null,
    review: UNREVIEWED,
  });
}

interface Row {
  name: string;
  item: NativeExamItem;
  arriving: NativeAnswerKeySuggestion;
  fits: boolean;
}

const ROWS: Row[] = [
  {
    name: "D1 single choice names a removed choice",
    item: choiceItem("single_choice", "absent", [], null, ["choice_001", "choice_002"]),
    arriving: keyedSuggestion({ correct_choice_ids: ["choice_003"] }),
    fits: false,
  },
  {
    name: "D2 multi names one removed choice",
    item: choiceItem("multiple_response", "absent", [], null, ["choice_001", "choice_002"]),
    arriving: keyedSuggestion({ correct_choice_ids: ["choice_001", "choice_003"] }),
    fits: false,
  },
  {
    name: "D3 multi names declared choices in another order",
    item: choiceItem("multiple_response", "absent", [], null),
    arriving: keyedSuggestion({ correct_choice_ids: ["choice_003", "choice_001"] }),
    fits: true,
  },
  {
    name: "D4 matching pairs a removed left entry",
    item: keylessMatchingItem(["left_001", "left_002"]),
    arriving: keyedSuggestion({ match_pairs: pairs(ARRIVING_PAIRS) }),
    fits: false,
  },
  {
    name: "D5 matching misses a left entry the teacher added",
    item: keylessMatchingItem(["left_001", "left_002", "left_003", "left_004"]),
    arriving: keyedSuggestion({ match_pairs: pairs(ARRIVING_PAIRS) }),
    fits: false,
  },
  {
    name: "D6 matching names a removed right entry",
    item: keylessMatchingItem(undefined, ["right_001", "right_002"]),
    arriving: keyedSuggestion({ match_pairs: pairs(ARRIVING_PAIRS) }),
    fits: false,
  },
  {
    name: "D7 matching pairs declared entries in another order",
    item: keylessMatchingItem(),
    arriving: keyedSuggestion({ match_pairs: pairs([...ARRIVING_PAIRS].reverse()) }),
    fits: true,
  },
  {
    name: "D8 gap names a removed gap",
    item: gapItem("absent", [["gap_001", []]], null),
    arriving: ARRIVING_GAPS,
    fits: false,
  },
  {
    name: "D8 gap names a removed gap on a key that follows its previous suggestion",
    item: gapItem("machine_proposed", [["gap_001", ["Anna"]]], gapSuggestion([["gap_001", ["Anna"]]])),
    arriving: ARRIVING_GAPS,
    fits: false,
  },
  {
    name: "D9 gap misses a gap the teacher added",
    item: gapItem(
      "absent",
      [
        ["gap_001", []],
        ["gap_002", []],
        ["gap_003", []],
      ],
      null,
    ),
    arriving: ARRIVING_GAPS,
    fits: false,
  },
  {
    name: "D10 gap names the same gaps in another order",
    item: gapItem(
      "absent",
      [
        ["gap_002", []],
        ["gap_001", []],
      ],
      null,
    ),
    arriving: ARRIVING_GAPS,
    fits: true,
  },
  {
    name: "a choice suggestion never fits a gap question",
    item: gapItem("absent", [["gap_001", []]], null),
    arriving: keyedSuggestion({ correct_choice_ids: ["choice_001"] }),
    fits: false,
  },
];

describe("an arriving suggestion that does not fit its question is stored and never the key (P13)", () => {
  it.each(ROWS)("$name", (row) => {
    const arrived = withArrivingSuggestion(row.item, row.arriving);

    expect(arrived.ai_suggestion).toEqual(row.arriving);
    if (row.fits) {
      expect(arrived.answer_key.origin).toBe("machine_proposed");
      expect(arrived.answer_key.correct_choice_ids).toEqual(row.arriving.correct_choice_ids);
      expect(arrived.answer_key.match_pairs).toEqual(row.arriving.match_pairs);
      expect(arrived.review.state).toBe("review_required");
    } else {
      expect(arrived.answer_key).toEqual(row.item.answer_key);
      expect(arrived.gaps).toEqual(row.item.gaps);
      expect(arrived.review).toEqual(row.item.review);
    }
  });
});

describe("restoring a kept suggestion that does not fit (T6, P13)", () => {
  it("leaves the question unchanged", () => {
    const item = choiceItem(
      "single_choice",
      "teacher_authored",
      ["choice_001"],
      keyedSuggestion({ correct_choice_ids: ["choice_003"] }),
      ["choice_001", "choice_002"],
    );

    expect(withRestoredSuggestion(item)).toEqual(item);
  });

  it("restores a kept suggestion that fits", () => {
    const kept = keyedSuggestion({ correct_choice_ids: ["choice_002"] });
    const item = choiceItem("single_choice", "teacher_authored", ["choice_001"], kept);

    const restored = withRestoredSuggestion(item);

    expect(restored.answer_key).toEqual({
      correct_choice_ids: ["choice_002"],
      match_pairs: [],
      origin: "machine_proposed",
    });
    expect(restored.review.state).toBe("review_required");
  });
});
