import { describe, expect, it } from "vitest";

import {
  buildMissingRiskContextMessage,
  mapMissingRiskContextFieldLabels,
} from "./riskExportGate";

describe("riskExportGate", () => {
  it("maps backend field keys to Swedish labels", () => {
    expect(mapMissingRiskContextFieldLabels(["scope", "assessment_date", "next_review_date"])).toEqual([
      "omfattning",
      "datum",
      "nästa översyn",
    ]);
  });

  it("keeps unknown fields as fallback labels", () => {
    expect(mapMissingRiskContextFieldLabels(["unknown_field"])).toEqual(["unknown_field"]);
  });

  it("builds a concise missing-context message from backend keys", () => {
    expect(buildMissingRiskContextMessage(["scope", "participants"])).toBe(
      "Fyll i omfattning, deltagare innan export.",
    );
  });

  it("returns null when no fields are missing", () => {
    expect(buildMissingRiskContextMessage([])).toBeNull();
    expect(buildMissingRiskContextMessage(null)).toBeNull();
  });
});
