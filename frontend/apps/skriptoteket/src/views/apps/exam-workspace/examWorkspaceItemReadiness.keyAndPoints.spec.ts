import { describe, expect, it } from "vitest";

import { examWorkspaceItemReadiness } from "./examWorkspaceItemReadiness";
import { buildChoiceItem } from "./examWorkspaceItemReadiness.specSupport";
import { buildGap } from "./examWorkspaceKeyedItems.specSupport";

describe("examWorkspaceItemReadiness key and points states", () => {
  it("reports a missing key only for keyed kinds", () => {
    const keyed = buildChoiceItem({
      answer_key: { correct_choice_ids: [], match_pairs: [], origin: "absent" },
    });
    const freeText = buildChoiceItem({
      answer_key: { correct_choice_ids: [], match_pairs: [], origin: "not_applicable" },
      choices: [],
      kind: "free_text",
      match_left: [],
      match_right: [],
    });

    expect(examWorkspaceItemReadiness(keyed)).toEqual(["missing_answer_key"]);
    expect(examWorkspaceItemReadiness(freeText)).toEqual([]);
  });

  it("reports a partial gap key", () => {
    const item = buildChoiceItem({
      choices: [],
      gaps: [
        buildGap("gap_001", ["100"]),
        buildGap("gap_002"),
      ],
      kind: "gap_fill",
      match_left: [],
      match_right: [],
    });

    expect(examWorkspaceItemReadiness(item)).toEqual(["partial_gap_key"]);
  });

  it("still blocks export for a keyed gap item with an empty gap", () => {
    const draft = buildChoiceItem({
      choices: [],
      gaps: [
        buildGap("gap_001", ["100"]),
        buildGap("gap_002"),
      ],
      kind: "gap_fill",
      match_left: [],
      match_right: [],
    });

    expect(examWorkspaceItemReadiness(draft)).toEqual(["partial_gap_key"]);
  });

  it("reports no empty gap for a question without an answer key", () => {
    const unkeyed = buildChoiceItem({
      answer_key: { correct_choice_ids: [], match_pairs: [], origin: "absent" },
      choices: [],
      gaps: [
        buildGap("gap_001", ["100"]),
        buildGap("gap_002"),
      ],
      kind: "gap_fill",
      match_left: [],
      match_right: [],
    });

    expect(examWorkspaceItemReadiness(unkeyed)).toEqual(["missing_answer_key"]);
  });

  it("accepts zero points and positive fractions, but reports negative points", () => {
    expect(examWorkspaceItemReadiness(buildChoiceItem({ points: 0 }))).toEqual([]);
    expect(examWorkspaceItemReadiness(buildChoiceItem({ points: -2 }))).toEqual([
      "negative_points",
    ]);
    expect(examWorkspaceItemReadiness(buildChoiceItem({ points: 0.5 }))).toEqual([]);
  });

  it.each([Number.NaN, Number.POSITIVE_INFINITY, Number.NEGATIVE_INFINITY])(
    "reports non-finite points %s",
    (points) => {
      expect(examWorkspaceItemReadiness(buildChoiceItem({ points }))).toEqual([
        "negative_points",
      ]);
    },
  );

  it("reports choices without exportable text, including whitespace", () => {
    const empty = buildChoiceItem({
      choices: [
        { choice_id: "choice_001", body: [{ heading_level: null, segments: [{ kind: "text", marks: [], text: "Syre" }] }] },
        { choice_id: "choice_002", body: [{ heading_level: null, segments: [{ kind: "text", marks: [], text: "" }] }] },
      ],
    });
    const blank = buildChoiceItem({
      choices: [
        { choice_id: "choice_001", body: [{ heading_level: null, segments: [{ kind: "text", marks: [], text: "Syre" }] }] },
        { choice_id: "choice_002", body: [{ heading_level: null, segments: [{ kind: "text", marks: [], text: " " }] }] },
      ],
    });

    expect(examWorkspaceItemReadiness(empty)).toEqual(["empty_choice"]);
    expect(examWorkspaceItemReadiness(blank)).toEqual(["empty_choice"]);
  });
});
