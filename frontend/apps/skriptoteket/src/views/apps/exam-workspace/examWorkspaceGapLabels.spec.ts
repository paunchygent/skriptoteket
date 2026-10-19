import { describe, expect, it } from "vitest";

import { examGapStates, gapChipLabel, gapNumberIn } from "./examWorkspaceGapLabels";
import { buildGap } from "./examWorkspaceKeyedItems.specSupport";
import { plainBody } from "./examWorkspaceRichText";

/** A dropdown gap with the given option texts and correct option, by index, or none. */
function dropdownGap(gapId: string, texts: string[], correctIndex: number | null): ReturnType<typeof buildGap> {
  return buildGap(gapId, [], {
    correct_option_id: correctIndex === null ? null : `choice_00${correctIndex + 1}`,
    options: texts.map((text, index) => ({ body: plainBody(text), choice_id: `choice_00${index + 1}` })),
  });
}

describe("gapChipLabel", () => {
  it("joins accepted values or falls back to the gap number", () => {
    expect(gapChipLabel(buildGap("gap_001", ["Stockholm", "Sthlm"]), 1, "gap_fill")).toBe("Stockholm / Sthlm");
    expect(gapChipLabel(buildGap("gap_002"), 2, "gap_fill")).toBe("Lucka 2");
    expect(gapChipLabel(undefined, 0, "gap_fill")).toBe("Lucka");
  });

  it("shows a dropdown gap's correct option text, or the gap number without one", () => {
    expect(gapChipLabel(dropdownGap("gap_001", ["R", "A", "B"], 1), 1, "inline_choice")).toBe("A");
    expect(gapChipLabel(dropdownGap("gap_001", ["R", "A", "B"], null), 1, "inline_choice")).toBe("Lucka 1");
    expect(gapChipLabel(dropdownGap("gap_001", [], null), 1, "inline_choice")).toBe("Lucka 1");
    expect(gapChipLabel(undefined, 0, "inline_choice")).toBe("Lucka");
  });
});

describe("examGapStates", () => {
  it("numbers gaps by declared order, not by where the text places them", () => {
    const states = examGapStates([buildGap("gap_007"), buildGap("gap_001", ["Paris"])], "gap_fill");

    expect(states.gap_007).toEqual({
      label: "Lucka 1",
      accessibleLabel: "Lucka 1, saknar godkända svar",
      empty: true,
    });
    expect(states.gap_001).toEqual({
      label: "Paris",
      accessibleLabel: "Lucka 2, godkända svar: Paris",
      empty: false,
    });
    expect(gapNumberIn([buildGap("gap_007")], "gap_009")).toBe(0);
  });

  it("describes a dropdown gap's options state instead of its accepted values", () => {
    expect(examGapStates([dropdownGap("gap_001", ["R", "A", "B"], 1)], "inline_choice").gap_001).toEqual({
      label: "A",
      accessibleLabel: "Lucka 1, rullista med alternativen R, A, B, rätt alternativ: A",
      empty: false,
    });
    expect(examGapStates([dropdownGap("gap_001", ["R", "A", "B"], null)], "inline_choice").gap_001).toEqual({
      label: "Lucka 1",
      accessibleLabel: "Lucka 1, rullista med alternativen R, A, B, saknar rätt alternativ",
      empty: true,
    });
    expect(examGapStates([dropdownGap("gap_001", [], null)], "inline_choice").gap_001).toEqual({
      label: "Lucka 1",
      accessibleLabel: "Lucka 1, rullista utan alternativ",
      empty: true,
    });
  });

  it("treats a dropdown gap whose correct option names no declared option as unanswered", () => {
    const gap = {
      ...dropdownGap("gap_001", ["R", "A", "B"], null),
      correct_option_id: "choice_009",
    };
    expect(examGapStates([gap], "inline_choice").gap_001).toEqual({
      label: "Lucka 1",
      accessibleLabel: "Lucka 1, rullista med alternativen R, A, B, saknar rätt alternativ",
      empty: true,
    });
  });
});
