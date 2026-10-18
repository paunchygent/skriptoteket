/**
 * Dropdown (inline_choice) readiness: option count and a correct option in every gap.
 */
import { describe, expect, it } from "vitest";

import type { NativeExamChoice, NativeExamGap, NativeExamItem } from "../../../api/examWorkspace";
import { GAP_WITHOUT_CORRECT_OPTION_GUIDANCE } from "./examWorkspaceAnswerKeyRules";
import { withGapOptions } from "./examWorkspaceItemEdits";
import {
  examWorkspaceItemReadiness,
  examWorkspaceReadinessByItemId,
} from "./examWorkspaceItemReadiness";
import { buildChoiceItem } from "./examWorkspaceItemReadiness.specSupport";
import { buildGap } from "./examWorkspaceKeyedItems.specSupport";
import { plainBody } from "./examWorkspaceRichText";

function option(choiceId: string, text: string): NativeExamChoice {
  return { choice_id: choiceId, body: plainBody(text) };
}

const TWO_OPTIONS = [option("option_001", "Syre"), option("option_002", "Järn")];

function keyedGap(gapId: string, options: NativeExamChoice[]): NativeExamGap {
  return buildGap(gapId, [], { correct_option_id: options[0]?.choice_id ?? "option_001", options });
}

function dropdown(gaps: NativeExamGap[], kind: NativeExamItem["kind"] = "inline_choice"): NativeExamItem {
  return buildChoiceItem({
    kind,
    choices: [],
    answer_key: { origin: "teacher_authored", correct_choice_ids: [], match_pairs: [] },
    body: [{ heading_level: null, segments: gaps.map((gap) => ({ kind: "gap" as const, gap_id: gap.gap_id })) }],
    gaps,
  });
}

describe("dropdown option count", () => {
  it("blocks a gap with one option", () => {
    const item = dropdown([keyedGap("gap_001", [TWO_OPTIONS[0]!])]);
    expect(examWorkspaceItemReadiness(item)).toEqual(["too_few_gap_options"]);
  });

  it("passes a gap with two options", () => {
    expect(examWorkspaceItemReadiness(dropdown([keyedGap("gap_001", TWO_OPTIONS)]))).toEqual([]);
  });

  it("reports one reason when only the last of three gaps is short", () => {
    const item = dropdown([
      keyedGap("gap_001", TWO_OPTIONS),
      keyedGap("gap_002", TWO_OPTIONS),
      keyedGap("gap_003", [TWO_OPTIONS[0]!]),
    ]);
    expect(examWorkspaceItemReadiness(item)).toEqual(["too_few_gap_options"]);
  });

  it("reports a blank single option as empty and too few", () => {
    const item = dropdown([keyedGap("gap_001", [option("option_001", " ")])]);
    expect(examWorkspaceItemReadiness(item)).toEqual(["empty_gap_option", "too_few_gap_options"]);
  });

  it("never applies to a gap_fill", () => {
    const item = dropdown([buildGap("gap_001", ["Syre"])], "gap_fill");
    expect(examWorkspaceItemReadiness(item)).not.toContain("too_few_gap_options");
  });
});

describe("dropdown without a correct option", () => {
  function unkeyed(): NativeExamItem {
    return {
      ...dropdown([buildGap("gap_001", [], { correct_option_id: null, options: TWO_OPTIONS })]),
      answer_key: { origin: "source_provided", correct_choice_ids: [], match_pairs: [] },
    };
  }

  it("blocks with its guidance copy", () => {
    const item = unkeyed();
    expect(examWorkspaceItemReadiness(item)).toContain("gap_without_correct_option");
    expect(GAP_WITHOUT_CORRECT_OPTION_GUIDANCE).toBe("Markera rätt alternativ i varje rullista.");
    expect(examWorkspaceReadinessByItemId([item])[item.item_id]).toContain(
      "Markera rätt alternativ i varje rullista.",
    );
  });

  it("clears once a correct option is selected", () => {
    const result = withGapOptions(unkeyed(), "gap_001", TWO_OPTIONS, "option_002");
    expect(examWorkspaceItemReadiness(result)).not.toContain("gap_without_correct_option");
  });

  it("never applies to a gap_fill", () => {
    const item = dropdown([buildGap("gap_001", ["Syre"])], "gap_fill");
    expect(examWorkspaceItemReadiness(item)).not.toContain("gap_without_correct_option");
  });
});
