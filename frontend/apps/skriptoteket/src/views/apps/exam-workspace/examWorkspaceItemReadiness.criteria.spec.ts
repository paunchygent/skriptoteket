import { describe, expect, it } from "vitest";

import type { NativeExamItem } from "../../../api/examWorkspace";
import {
  examWorkspaceItemReadiness,
  examWorkspaceReadinessByItemId,
} from "./examWorkspaceItemReadiness";
import { buildChoiceItem } from "./examWorkspaceItemReadiness.specSupport";
import {
  CRITERIA_POINTS_MISMATCH_GUIDANCE,
  INVALID_CRITERION_POINTS_GUIDANCE,
} from "./examWorkspaceItemSaveRules";

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

  it("maps the criteria reasons to their Swedish copy by item id", () => {
    const item = buildCriteriaItem({ points: 2 });

    expect(examWorkspaceReadinessByItemId([item])).toEqual({
      item_001: [CRITERIA_POINTS_MISMATCH_GUIDANCE],
    });
  });

  it("maps invalid criterion points to their Swedish copy by item id", () => {
    const item = buildCriteriaItem({
      criteria: [
        { points: 1.5, text: "Definition" },
        { points: 1.5, text: "Exempel" },
      ],
    });

    expect(examWorkspaceReadinessByItemId([item])).toEqual({
      item_001: [INVALID_CRITERION_POINTS_GUIDANCE],
    });
  });
});
