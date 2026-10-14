/**
 * Exam workspace item save rules.
 *
 * Expected behavior:
 *   The save refusal copy names every question that breaks a server item
 *   rule, one sentence group per rule in a stable order (partial gap key,
 *   points not greater than zero, choice without text), and is `null` when
 *   the server would accept every item.
 */

import { describe, expect, it } from "vitest";

import type { NativeExamItem } from "../../../api/examWorkspace";
import { examWorkspaceSaveRefusalCopy } from "./examWorkspaceItemSaveRules";
import { INCOMPLETE_MATCH_KEY_GUIDANCE } from "./examWorkspaceAnswerKeyRules";
import {
  buildMatchingItem,
  buildMatchingItemWithDistractor,
  buildMatchingItemWithPairs,
} from "./examWorkspaceMatchingItem.specSupport";

function buildChoiceItem(
  sequence: number,
  overrides: Partial<NativeExamItem> = {},
): NativeExamItem {
  return {
    ai_suggestion: null,
    facit_text: null,
    marking_guide: null,
    printed_label: null,
    retry_source: null,
    answer_key: { correct_choice_ids: ["choice_a"], match_pairs: [], origin: "teacher_authored" },
    body: [{ segments: [{ kind: "text", text: "Vilket ämne är en gas?" }] }],
    choices: [
      { choice_id: "choice_a", text: "Syre" },
      { choice_id: "choice_b", text: "Järn" },
    ],
    gaps: [],
    item_id: `item_00${sequence}`,
    kind: "single_choice",
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
    sequence,
    source_anchor: null,
    ...overrides,
  };
}

const EMPTY_CHOICES = [
  { choice_id: "choice_a", text: "Syre" },
  { choice_id: "choice_b", text: "" },
];

describe("examWorkspaceSaveRefusalCopy", () => {
  it("is null when every item can be saved, including missing points", () => {
    expect(
      examWorkspaceSaveRefusalCopy([buildChoiceItem(1), buildChoiceItem(2, { points: null })]),
    ).toBeNull();
  });

  it("names one question with points that are not greater than zero", () => {
    expect(examWorkspaceSaveRefusalCopy([buildChoiceItem(1, { points: -1 })])).toBe(
      "Fråga 1 har noll eller negativa poäng. Poängen måste vara större än noll.",
    );
  });

  it("names every question in each rule, rule by rule", () => {
    const items = [
      buildChoiceItem(1, { points: 0 }),
      buildChoiceItem(2, { choices: EMPTY_CHOICES }),
      buildChoiceItem(3, { choices: EMPTY_CHOICES, points: 0 }),
    ];

    expect(examWorkspaceSaveRefusalCopy(items)).toBe(
      "Frågorna 1 och 3 har noll eller negativa poäng. Poängen måste vara större än noll. " +
        "Frågorna 2 och 3 har svarsalternativ utan text. Skriv text i varje svarsalternativ.",
    );
  });
});

describe("examWorkspaceSaveRefusalCopy for matching items", () => {
  it("is null for a fully keyed matching item", () => {
    expect(examWorkspaceSaveRefusalCopy([buildMatchingItem()])).toBeNull();
  });

  it("is null for a keyed matching item with an unpaired right entry", () => {
    expect(examWorkspaceSaveRefusalCopy([buildMatchingItemWithDistractor()])).toBeNull();
  });

  it("is null once every pair is cleared and the key becomes absent", () => {
    const item = buildMatchingItemWithPairs([]);

    expect(
      examWorkspaceSaveRefusalCopy([
        { ...item, answer_key: { ...item.answer_key, origin: "absent" } },
      ]),
    ).toBeNull();
  });

  it("refuses a keyed item missing one pair with the matching guidance", () => {
    expect(
      examWorkspaceSaveRefusalCopy([
        buildMatchingItemWithPairs([
          [1, 2],
          [2, 1],
        ]),
      ]),
    ).toBe(
      `Fråga 1 har en matchning där facit inte är komplett. ${INCOMPLETE_MATCH_KEY_GUIDANCE}`,
    );
  });

  it("refuses a keyed item that uses a right entry twice", () => {
    expect(
      examWorkspaceSaveRefusalCopy([
        buildMatchingItemWithPairs([
          [1, 2],
          [2, 2],
          [3, 3],
        ]),
      ]),
    ).toBe(
      `Fråga 1 har en matchning där facit inte är komplett. ${INCOMPLETE_MATCH_KEY_GUIDANCE}`,
    );
  });

  it("refuses an empty left or right entry text", () => {
    const item = buildMatchingItem();
    const emptyLeft = {
      ...item,
      match_left: item.match_left.map((entry) =>
        entry.left_id === "left_002" ? { ...entry, text: "" } : entry,
      ),
    };

    expect(examWorkspaceSaveRefusalCopy([emptyLeft])).toBe(
      "Fråga 1 har rader eller svar i matchningen utan text. Skriv text i varje rad och varje svar.",
    );
  });
});
