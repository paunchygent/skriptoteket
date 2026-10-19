import { describe, expect, it } from "vitest";

import { examGapStates, gapChipLabel, gapNumberIn } from "./examWorkspaceGapLabels";
import { buildGap } from "./examWorkspaceKeyedItems.specSupport";

describe("gapChipLabel", () => {
  it("joins accepted values or falls back to the gap number", () => {
    expect(gapChipLabel(buildGap("gap_001", ["Stockholm", "Sthlm"]), 1)).toBe("Stockholm / Sthlm");
    expect(gapChipLabel(buildGap("gap_002"), 2)).toBe("Lucka 2");
    expect(gapChipLabel(undefined, 0)).toBe("Lucka");
  });
});

describe("examGapStates", () => {
  it("numbers gaps by declared order, not by where the text places them", () => {
    const states = examGapStates([buildGap("gap_007"), buildGap("gap_001", ["Paris"])]);

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
});
