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

function buildChoiceItem(
  sequence: number,
  overrides: Partial<NativeExamItem> = {},
): NativeExamItem {
  return {
    answer_key: { correct_choice_ids: ["choice_a"], origin: "teacher_authored" },
    body: [{ segments: [{ kind: "text", text: "Vilket ämne är en gas?" }] }],
    choices: [
      { choice_id: "choice_a", text: "Syre" },
      { choice_id: "choice_b", text: "Järn" },
    ],
    gaps: [],
    item_id: `item_00${sequence}`,
    kind: "single_choice",
    points: 1,
    review: {
      confidence: 0.95,
      parse_origin: "deterministic",
      reasons: [],
      state: "review_complete",
    },
    sequence,
    source_anchor: null,
    title: null,
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
