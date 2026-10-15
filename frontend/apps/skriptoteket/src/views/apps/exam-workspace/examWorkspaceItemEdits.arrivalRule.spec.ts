/**
 * The rule that decides whether an arriving AI suggestion becomes the key
 * (TASK-SKRIPT-39-04-07 T5 as amended by P12).
 *
 * Expected behavior:
 *   The arriving suggestion is always kept on its question. It becomes the
 *   key — `machine_proposed`, review required — only where the question has
 *   no key or its key is an unreviewed `machine_proposed` key equal to the
 *   previous suggestion. A source, teacher or reviewed key stays even when
 *   it equals the previous suggestion. Restoring the kept suggestion (T6)
 *   makes it the key from any origin.
 *
 * Rows follow the P12 matrix in the retained design note
 * `evidence/implementation/TASK-SKRIPT-39-04-07/p12/design.md`.
 */

import { describe, expect, it } from "vitest";

import type { NativeAnswerKeySuggestion, NativeExamItem } from "../../../api/examWorkspace";
import { withArrivingSuggestion, withRestoredSuggestion } from "./examWorkspaceItemEdits";

type Origin = NativeExamItem["answer_key"]["origin"];
type ReviewState = NativeExamItem["review"]["state"];

const KEY = ["choice_001"];
const OTHER = ["choice_003"];
const ARRIVING_DIFFERS = ["choice_002"];

interface Relation {
  name: string;
  previous: string[] | null;
  arriving: string[];
}

const NO_PREVIOUS: Relation = { name: "no previous", previous: null, arriving: ARRIVING_DIFFERS };
const NO_PREVIOUS_ARRIVING_EQUALS_KEY: Relation = {
  name: "no previous, arriving equals key",
  previous: null,
  arriving: KEY,
};
const EQUALS_PREVIOUS: Relation = {
  name: "key equals previous",
  previous: KEY,
  arriving: ARRIVING_DIFFERS,
};
const EQUALS_PREVIOUS_AND_ARRIVING: Relation = {
  name: "key equals previous and arriving",
  previous: KEY,
  arriving: KEY,
};
const DIFFERS: Relation = { name: "key differs from both", previous: OTHER, arriving: ARRIVING_DIFFERS };
const DIFFERS_EQUALS_ARRIVING: Relation = {
  name: "key differs from previous, equals arriving",
  previous: OTHER,
  arriving: KEY,
};
const ALL_RELATIONS = [
  NO_PREVIOUS,
  NO_PREVIOUS_ARRIVING_EQUALS_KEY,
  EQUALS_PREVIOUS,
  EQUALS_PREVIOUS_AND_ARRIVING,
  DIFFERS,
  DIFFERS_EQUALS_ARRIVING,
];
const TRUSTED: Origin[] = ["source_provided", "teacher_authored", "reviewed_advisory"];
const BOTH_STATES: ReviewState[] = ["review_required", "review_complete"];
const RESTORABLE: Origin[] = ["machine_proposed", ...TRUSTED];

interface Row {
  matrixRow: string;
  origin: Origin;
  state: ReviewState;
  relation: Relation;
  becomesKey: boolean;
}

function rows(
  matrixRow: string,
  origins: Origin[],
  states: ReviewState[],
  relations: Relation[],
  becomesKey: boolean,
): Row[] {
  return origins.flatMap((origin) =>
    states.flatMap((state) =>
      relations.map((relation) => ({ matrixRow, origin, state, relation, becomesKey })),
    ),
  );
}

const MATRIX: Row[] = [
  ...rows("3-4", ["machine_proposed"], ["review_required"], [EQUALS_PREVIOUS, EQUALS_PREVIOUS_AND_ARRIVING], true),
  ...rows(
    "5-7",
    ["machine_proposed"],
    ["review_required"],
    [DIFFERS, DIFFERS_EQUALS_ARRIVING, NO_PREVIOUS, NO_PREVIOUS_ARRIVING_EQUALS_KEY],
    false,
  ),
  ...rows("8-10", ["machine_proposed"], ["review_complete"], ALL_RELATIONS, false),
  ...rows("11-15", TRUSTED, BOTH_STATES, ALL_RELATIONS, false),
];

function suggestion(choiceIds: string[]): NativeAnswerKeySuggestion {
  return {
    correct_choice_ids: [...choiceIds],
    fingerprint: "a".repeat(64),
    gap_accepted_values: [],
    match_pairs: [],
    model: "model",
    prompt_template_version: "v1",
    provider_profile_id: "profile",
  };
}

function choiceItem(
  origin: Origin,
  correctChoiceIds: string[],
  state: ReviewState,
  previous: NativeAnswerKeySuggestion | null,
  kind: NativeExamItem["kind"] = "single_choice",
): NativeExamItem {
  return {
    ai_suggestion: previous,
    facit_text: null,
    criteria: [],
    printed_label: null,
    retry_source: null,
    answer_key: { correct_choice_ids: [...correctChoiceIds], match_pairs: [], origin },
    body: [{ segments: [{ kind: "text", text: "Vilket är huvudordet?" }] }],
    choices: [
      { choice_id: "choice_001", text: "vägen" },
      { choice_id: "choice_002", text: "eleverna" },
      { choice_id: "choice_003", text: "skolan" },
    ],
    gaps: [],
    item_id: "item_001",
    kind,
    match_left: [],
    match_right: [],
    points: 1,
    points_estimated: false,
    review: { confidence: null, parse_origin: "teacher_created", reasons: [], state },
    sequence: 1,
    source_anchor: null,
  };
}

function expectBecameKey(arrived: NativeExamItem, arriving: NativeAnswerKeySuggestion): void {
  expect(arrived.ai_suggestion).toEqual(arriving);
  expect(arrived.answer_key).toEqual({
    correct_choice_ids: arriving.correct_choice_ids,
    match_pairs: [],
    origin: "machine_proposed",
  });
  expect(arrived.review.state).toBe("review_required");
}

function expectKeyStayed(
  arrived: NativeExamItem,
  item: NativeExamItem,
  arriving: NativeAnswerKeySuggestion,
): void {
  expect(arrived.ai_suggestion).toEqual(arriving);
  expect(arrived.answer_key).toEqual(item.answer_key);
  expect(arrived.review).toEqual(item.review);
}

describe("withArrivingSuggestion follows the P12 arrival rule", () => {
  it.each(MATRIX.map((row) => [
    `row ${row.matrixRow}: ${row.origin}, ${row.state}, ${row.relation.name}`,
    row,
  ] as const))("%s", (_name, row) => {
    const previous = row.relation.previous ? suggestion(row.relation.previous) : null;
    const item = choiceItem(row.origin, KEY, row.state, previous);
    const arriving = suggestion(row.relation.arriving);

    const arrived = withArrivingSuggestion(item, arriving);

    if (row.becomesKey) {
      expectBecameKey(arrived, arriving);
    } else {
      expectKeyStayed(arrived, item, arriving);
    }
  });

  it.each(
    BOTH_STATES.flatMap((state) =>
      [null, ARRIVING_DIFFERS, OTHER].map((previous) => [state, previous] as const),
    ),
  )("rows 1-2: a keyless %s question with previous %j takes the suggestion as key", (state, previous) => {
    const item = choiceItem("absent", [], state, previous ? suggestion(previous) : null);
    const arriving = suggestion(ARRIVING_DIFFERS);

    expectBecameKey(withArrivingSuggestion(item, arriving), arriving);
  });

  it("row 17: a key equal to the previous suggestion in another order follows it", () => {
    const item = choiceItem(
      "machine_proposed",
      ["choice_001", "choice_002"],
      "review_required",
      suggestion(["choice_002", "choice_001"]),
      "multiple_response",
    );
    const arriving = suggestion(["choice_003"]);

    expectBecameKey(withArrivingSuggestion(item, arriving), arriving);
  });
});

describe("withRestoredSuggestion ignores the arrival rule (T6)", () => {
  it.each(
    RESTORABLE.flatMap((origin) =>
      BOTH_STATES.map((state) => [origin, state] as const),
    ),
  )("restores a kept suggestion as the key over a %s, %s key", (origin, state) => {
    const item = choiceItem(origin, KEY, state, null);
    const arriving = suggestion(ARRIVING_DIFFERS);
    const stayed = withArrivingSuggestion(item, arriving);
    expect(stayed.answer_key.origin).toBe(origin);

    expectBecameKey(withRestoredSuggestion(stayed), arriving);
  });
});
