/**
 * Exam workspace item edits: dropdown gap options.
 *
 * Expected behavior:
 *   `withGapOptions` replaces the options and correct option of exactly the
 *   named gap and returns the same item when the gap is missing or nothing
 *   changes.
 */

import { describe, expect, it } from "vitest";

import type { NativeExamChoice } from "../../../api/examWorkspace";
import { withGapOptions } from "./examWorkspaceItemEdits";
import { buildGap } from "./examWorkspaceKeyedItems.specSupport";
import { buildGapItem } from "./ExamWorkspaceBodyEditor.specSupport";
import { plainBody } from "./examWorkspaceRichText";

function choice(choiceId: string, text: string): NativeExamChoice {
  return { body: plainBody(text), choice_id: choiceId };
}

const OPTIONS = [choice("choice_001", "röd"), choice("choice_002", "blå")];

function dropdownItem() {
  return buildGapItem({
    kind: "inline_choice",
    gaps: [
      buildGap("gap_001", [], { options: OPTIONS, correct_option_id: "choice_001" }),
      buildGap("gap_002", [], { options: [choice("choice_001", "ja")], correct_option_id: "choice_001" }),
    ],
  });
}

describe("withGapOptions", () => {
  it("replaces only the target gap's options and correct option", () => {
    const item = dropdownItem();
    const next = [OPTIONS[1], OPTIONS[0], choice("choice_003", "grön")];

    const result = withGapOptions(item, "gap_001", next, "choice_003");

    expect(result.gaps[0].options).toEqual(next);
    expect(result.gaps[0].correct_option_id).toBe("choice_003");
    expect(result.gaps[1]).toBe(item.gaps[1]);
    expect(result.body).toBe(item.body);
    expect(item.gaps[0].options).toEqual(OPTIONS);
  });

  it("returns the same item when the gap is missing", () => {
    const item = dropdownItem();
    expect(withGapOptions(item, "gap_404", OPTIONS, "choice_001")).toBe(item);
  });

  it("returns the same item when options and correct option are unchanged", () => {
    const item = dropdownItem();
    expect(withGapOptions(item, "gap_001", [...OPTIONS], "choice_001")).toBe(item);
  });

  it("changes the item when only the correct option differs", () => {
    const item = dropdownItem();
    const result = withGapOptions(item, "gap_001", [...OPTIONS], "choice_002");
    expect(result).not.toBe(item);
    expect(result.gaps[0].correct_option_id).toBe("choice_002");
  });
});
