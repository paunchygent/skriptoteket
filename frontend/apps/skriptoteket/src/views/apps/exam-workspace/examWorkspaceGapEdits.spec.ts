/**
 * Exam workspace gap edits: answer state and unanswered-gap removal.
 *
 * Expected behavior (TASK-SKRIPT-40-04-13 H6):
 *   A Lucktext gap holds an answer while it has an accepted value; a
 *   dropdown gap holds one while its correct option names one of its
 *   declared options. Removing an unanswered gap's placement from the body
 *   lets the owner drop its record through `withBody`, so one structural
 *   body edit removes the gap in one undo step.
 */

import { describe, expect, it } from "vitest";

import type { NativeExamBodyParagraph } from "../../../api/examWorkspace";
import { plainBody } from "./examWorkspaceRichText";
import { bodyWithoutGap, gapHasAnswer } from "./examWorkspaceGapEdits";
import { buildGap } from "./examWorkspaceKeyedItems.specSupport";

describe("gapHasAnswer", () => {
  it("is false without a gap and true for a Lucktext gap with an accepted value", () => {
    expect(gapHasAnswer(undefined, "gap_fill")).toBe(false);
    expect(gapHasAnswer(buildGap("gap_001", []), "gap_fill")).toBe(false);
    expect(gapHasAnswer(buildGap("gap_001", ["hundra"]), "gap_fill")).toBe(true);
  });

  it("needs a correct option naming a declared option for a dropdown gap", () => {
    const options = [
      { body: plainBody("zebra"), choice_id: "choice_001" },
      { body: plainBody("apa"), choice_id: "choice_002" },
    ];
    expect(
      gapHasAnswer(buildGap("gap_001", [], { correct_option_id: null, options }), "inline_choice"),
    ).toBe(false);
    expect(gapHasAnswer(buildGap("gap_001", [], { correct_option_id: null }), "inline_choice")).toBe(
      false,
    );
    expect(
      gapHasAnswer(
        buildGap("gap_001", [], { correct_option_id: "choice_001", options }),
        "inline_choice",
      ),
    ).toBe(true);
    expect(
      gapHasAnswer(
        buildGap("gap_001", [], { correct_option_id: "choice_009", options }),
        "inline_choice",
      ),
    ).toBe(false);
  });
});

describe("bodyWithoutGap", () => {
  it("removes only the named gap's placement and keeps the other segments", () => {
    const body: NativeExamBodyParagraph[] = [
      {
        heading_level: null,
        segments: [
          { kind: "text", marks: [], text: "Vatten kokar vid " },
          { gap_id: "gap_001", kind: "gap" },
          { kind: "text", marks: [], text: " grader och fryser vid " },
          { gap_id: "gap_002", kind: "gap" },
          { kind: "text", marks: [], text: " grader." },
        ],
      },
    ];
    const next = bodyWithoutGap(body, "gap_002");
    expect(next[0]?.segments).toEqual([
      { kind: "text", marks: [], text: "Vatten kokar vid " },
      { gap_id: "gap_001", kind: "gap" },
      { kind: "text", marks: [], text: " grader och fryser vid " },
      { kind: "text", marks: [], text: " grader." },
    ]);
  });

  it("leaves an emptied paragraph without segments, as the editor writes one", () => {
    const body: NativeExamBodyParagraph[] = [
      { heading_level: null, segments: [{ gap_id: "gap_001", kind: "gap" }] },
    ];
    expect(bodyWithoutGap(body, "gap_001")).toEqual([{ heading_level: null, segments: [] }]);
  });
});
