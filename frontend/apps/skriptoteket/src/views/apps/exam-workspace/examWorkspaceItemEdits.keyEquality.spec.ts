/**
 * Whole-key equality behind the P12 arrival rule (TASK-SKRIPT-39-04-07).
 *
 * Expected behavior:
 *   An unreviewed `machine_proposed` key follows an arriving suggestion only
 *   when it equals the previous suggestion as a whole key: the same choice
 *   ids, the same match pairs and the same gap ids with the same accepted
 *   values, each compared as a set. Any extra, missing or different entry,
 *   including a historical id the question no longer declares, makes the key
 *   unequal, so the key stays.
 *
 * Rows follow case space B in the retained design note
 * `evidence/implementation/TASK-SKRIPT-39-04-07/repair3/design.md`.
 */

import { describe, expect, it } from "vitest";

import type { NativeAnswerKeySuggestion, NativeExamItem } from "../../../api/examWorkspace";
import { withArrivingSuggestion } from "./examWorkspaceSuggestionEdits";
import {
  UNREVIEWED,
  choiceItem,
  gapItem,
  gapSuggestion,
  keyedSuggestion as suggestion,
  pairs,
} from "./examWorkspaceKeyedItems.specSupport";
import type { GapValues } from "./examWorkspaceKeyedItems.specSupport";
import { buildMatchingItem } from "./examWorkspaceMatchingItem.specSupport";

function multiItem(key: string[], previous: NativeAnswerKeySuggestion): NativeExamItem {
  return choiceItem("multiple_response", "machine_proposed", key, previous);
}

function matchItem(key: Array<[string, string]>, previous: NativeAnswerKeySuggestion): NativeExamItem {
  return buildMatchingItem({
    ai_suggestion: previous,
    answer_key: { correct_choice_ids: [], match_pairs: pairs(key), origin: "machine_proposed" },
    review: UNREVIEWED,
  });
}

function machineGapItem(key: GapValues, previous: NativeAnswerKeySuggestion): NativeExamItem {
  return gapItem("machine_proposed", key, previous);
}

const ARRIVING_CHOICES = suggestion({ correct_choice_ids: ["choice_003"] });
const ARRIVING_PAIRS = suggestion({
  match_pairs: pairs([
    ["left_001", "right_003"],
    ["left_002", "right_002"],
    ["left_003", "right_001"],
  ]),
});
const ARRIVING_GAPS = gapSuggestion([
  ["gap_001", ["Bo"]],
  ["gap_002", ["Umeå"]],
]);

const KEY_PAIRS: Array<[string, string]> = [
  ["left_001", "right_002"],
  ["left_002", "right_001"],
  ["left_003", "right_003"],
];

interface Row {
  name: string;
  item: NativeExamItem;
  arriving: NativeAnswerKeySuggestion;
  equal: boolean;
}

const ROWS: Row[] = [
  {
    name: "B4 multi: reordered choices are equal",
    item: multiItem(["choice_001", "choice_002"], suggestion({ correct_choice_ids: ["choice_002", "choice_001"] })),
    arriving: ARRIVING_CHOICES,
    equal: true,
  },
  {
    name: "B5 multi: the previous suggestion is a subset of the key",
    item: multiItem(["choice_001", "choice_002"], suggestion({ correct_choice_ids: ["choice_001"] })),
    arriving: ARRIVING_CHOICES,
    equal: false,
  },
  {
    name: "B3 multi: the previous suggestion is a superset of the key",
    item: multiItem(["choice_001"], suggestion({ correct_choice_ids: ["choice_001", "choice_002"] })),
    arriving: ARRIVING_CHOICES,
    equal: false,
  },
  {
    name: "B6 multi: a duplicated key choice is not the previous suggestion's other choice",
    item: multiItem(["choice_001", "choice_001"], suggestion({ correct_choice_ids: ["choice_001", "choice_002"] })),
    arriving: ARRIVING_CHOICES,
    equal: false,
  },
  {
    name: "B7 multi: the previous suggestion also names a removed choice",
    item: multiItem(
      ["choice_001", "choice_002"],
      suggestion({ correct_choice_ids: ["choice_001", "choice_002", "choice_009"] }),
    ),
    arriving: ARRIVING_CHOICES,
    equal: false,
  },
  {
    name: "B8 matching: reordered pairs are equal",
    item: matchItem(KEY_PAIRS, suggestion({ match_pairs: pairs([...KEY_PAIRS].reverse()) })),
    arriving: ARRIVING_PAIRS,
    equal: true,
  },
  {
    name: "B9 matching: the previous suggestion is a subset of the key",
    item: matchItem(KEY_PAIRS, suggestion({ match_pairs: pairs(KEY_PAIRS.slice(0, 2)) })),
    arriving: ARRIVING_PAIRS,
    equal: false,
  },
  {
    name: "B10 matching: the previous suggestion holds an extra historical pair",
    item: matchItem(
      KEY_PAIRS,
      suggestion({ match_pairs: pairs([...KEY_PAIRS, ["left_009", "right_009"]]) }),
    ),
    arriving: ARRIVING_PAIRS,
    equal: false,
  },
  {
    name: "B11 matching: a duplicated key pair is not the previous suggestion's other pair",
    item: matchItem(
      [KEY_PAIRS[0], KEY_PAIRS[0], KEY_PAIRS[2]],
      suggestion({ match_pairs: pairs(KEY_PAIRS) }),
    ),
    arriving: ARRIVING_PAIRS,
    equal: false,
  },
  {
    name: "B12 gap: reordered values per gap are equal",
    item: machineGapItem(
      [["gap_001", ["Anna", "Anne"]], ["gap_002", ["Lund"]]],
      gapSuggestion([["gap_001", ["Anne", "Anna"]], ["gap_002", ["Lund"]]]),
    ),
    arriving: ARRIVING_GAPS,
    equal: true,
  },
  {
    name: "B13 gap: one gap's values are a subset of the key's",
    item: machineGapItem(
      [["gap_001", ["Anna", "Anne"]], ["gap_002", ["Lund"]]],
      gapSuggestion([["gap_001", ["Anna"]], ["gap_002", ["Lund"]]]),
    ),
    arriving: ARRIVING_GAPS,
    equal: false,
  },
  {
    name: "B14 gap: the previous suggestion holds an extra historical gap id",
    item: machineGapItem(
      [["gap_001", ["Anna"]], ["gap_002", ["Lund"]]],
      gapSuggestion([["gap_001", ["Anna"]], ["gap_002", ["Lund"]], ["gap_009", ["Malmö"]]]),
    ),
    arriving: ARRIVING_GAPS,
    equal: false,
  },
  {
    name: "B15 gap: the previous suggestion lacks a gap the key fills",
    item: machineGapItem(
      [["gap_001", ["Anna"]], ["gap_002", ["Lund"]]],
      gapSuggestion([["gap_001", ["Anna"]]]),
    ),
    arriving: ARRIVING_GAPS,
    equal: false,
  },
  {
    name: "B16 gap: a key gap without values carries no key data",
    item: machineGapItem([["gap_001", ["Anna"]], ["gap_002", []]], gapSuggestion([["gap_001", ["Anna"]]])),
    arriving: ARRIVING_GAPS,
    equal: true,
  },
  {
    name: "B17 gap: a duplicated key value is not the previous suggestion's other value",
    item: machineGapItem(
      [["gap_001", ["Anna", "Anna"]], ["gap_002", ["Lund"]]],
      gapSuggestion([["gap_001", ["Anna", "Anne"]], ["gap_002", ["Lund"]]]),
    ),
    arriving: ARRIVING_GAPS,
    equal: false,
  },
  {
    name: "B18 gap: a duplicated key value accepts nothing more",
    item: machineGapItem(
      [["gap_001", ["Anna", "Anna"]], ["gap_002", ["Lund"]]],
      gapSuggestion([["gap_001", ["Anna"]], ["gap_002", ["Lund"]]]),
    ),
    arriving: ARRIVING_GAPS,
    equal: true,
  },
  {
    name: "B19 cross family: a choice key never equals a gap suggestion",
    item: multiItem(["choice_001"], gapSuggestion([["gap_001", ["choice_001"]]])),
    arriving: ARRIVING_CHOICES,
    equal: false,
  },
];

describe("an unreviewed machine key follows an arrival only when it equals the whole previous suggestion", () => {
  it.each(ROWS)("$name", (row) => {
    const arrived = withArrivingSuggestion(row.item, row.arriving);

    expect(arrived.ai_suggestion).toEqual(row.arriving);
    if (row.equal) {
      expect(arrived.answer_key.origin).toBe("machine_proposed");
      expect(arrived.answer_key.correct_choice_ids).toEqual(row.arriving.correct_choice_ids);
      expect(arrived.answer_key.match_pairs).toEqual(row.arriving.match_pairs);
      for (const entry of row.arriving.gap_accepted_values) {
        expect(arrived.gaps.find((gap) => gap.gap_id === entry.gap_id)?.accepted_values).toEqual(
          entry.accepted_values,
        );
      }
    } else {
      expect(arrived.answer_key).toEqual(row.item.answer_key);
      expect(arrived.gaps).toEqual(row.item.gaps);
    }
    expect(arrived.review.state).toBe("review_required");
  });
});
