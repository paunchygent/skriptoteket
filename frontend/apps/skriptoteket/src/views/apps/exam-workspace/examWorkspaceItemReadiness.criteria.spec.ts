import { describe, expect, it } from "vitest";

import type { NativeExamItem } from "../../../api/examWorkspace";
import { examWorkspaceItemReadiness } from "./examWorkspaceItemReadiness";
import { buildChoiceItem } from "./examWorkspaceItemReadiness.specSupport";

function buildCriteriaItem(overrides: Partial<NativeExamItem> = {}): NativeExamItem {
  return {
    ...buildChoiceItem({
      answer_key: { correct_choice_ids: [], match_pairs: [], origin: "not_applicable" },
      choices: [],
      kind: "free_text",
      points: 3,
    }),
    criteria: [
      { points: 2, text: "Definition" },
      { points: 1, text: "Exempel" },
    ],
    ...overrides,
  };
}

describe("examWorkspaceItemReadiness for free-text criteria", () => {
  it("reports nothing when a non-empty criteria list sums to the item's points", () => {
    expect(examWorkspaceItemReadiness(buildCriteriaItem())).toEqual([]);
  });

  it("reports a criterion whose text is empty or whitespace only", () => {
    const blank = buildCriteriaItem({
      criteria: [
        { points: 2, text: " \n\t " },
        { points: 1, text: "Exempel" },
      ],
    });

    expect(examWorkspaceItemReadiness(blank)).toEqual(["empty_criterion_text"]);
  });

  it("reports criteria reasons in a stable order", () => {
    const item = buildCriteriaItem({
      criteria: [{ points: 1.5, text: "" }],
    });

    expect(examWorkspaceItemReadiness(item)).toEqual([
      "empty_criterion_text",
      "invalid_criterion_points",
      "criteria_points_mismatch",
    ]);
  });

  it("reports criteria on a question that is not free text", () => {
    const item = buildChoiceItem({ criteria: [{ points: 1, text: "Definition" }] });

    expect(examWorkspaceItemReadiness(item)).toEqual(["criteria_on_wrong_kind"]);
  });

  it("reports a criteria sum that is not the item's points", () => {
    const item = buildCriteriaItem({ points: 2 });

    expect(examWorkspaceItemReadiness(item)).toEqual(["criteria_points_mismatch"]);
  });

  it("reports invalid criterion points", () => {
    const item = buildCriteriaItem({
      criteria: [
        { points: 1.5, text: "Definition" },
        { points: 1.5, text: "Exempel" },
      ],
    });

    expect(examWorkspaceItemReadiness(item)).toEqual(["invalid_criterion_points"]);
  });
});
