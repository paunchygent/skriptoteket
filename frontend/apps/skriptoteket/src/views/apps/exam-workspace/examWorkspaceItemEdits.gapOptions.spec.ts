/**
 * Exam workspace item edits: dropdown gap options.
 *
 * Expected behavior:
 *   `withGapOptions` replaces the options and correct option of exactly the
 *   named gap and returns the same item when the gap is missing or nothing
 *   changes.
 */

import { describe, expect, it } from "vitest";

import type { NativeExamAnswerKeyOrigin, NativeExamChoice } from "../../../api/examWorkspace";
import { withGapOptions } from "./examWorkspaceItemEdits";
import { buildGap } from "./examWorkspaceKeyedItems.specSupport";
import { buildGapItem } from "./ExamWorkspaceBodyEditor.specSupport";
import { plainBody } from "./examWorkspaceRichText";

function choice(choiceId: string, text: string): NativeExamChoice {
  return { body: plainBody(text), choice_id: choiceId };
}

const OPTIONS = [choice("choice_001", "röd"), choice("choice_002", "blå")];

function dropdownItem(origin: NativeExamAnswerKeyOrigin = "teacher_authored") {
  return buildGapItem({
    kind: "inline_choice",
    answer_key: { correct_choice_ids: [], match_pairs: [], origin },
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

  describe("key ownership", () => {
    const UNAPPROVED = ["ai_interpreted", "machine_proposed"] as const;

    it.each(UNAPPROVED)("a changed correct option on a %s key makes it teacher authored", (origin) => {
      const result = withGapOptions(dropdownItem(origin), "gap_001", [...OPTIONS], "choice_002");
      expect(result.answer_key.origin).toBe("teacher_authored");
    });

    it.each(UNAPPROVED)("a text edit on a %s key keeps the origin", (origin) => {
      const edited = [choice("choice_001", "rosa"), OPTIONS[1]];
      const result = withGapOptions(dropdownItem(origin), "gap_001", edited, "choice_001");
      expect(result.gaps[0].options).toEqual(edited);
      expect(result.answer_key.origin).toBe(origin);
    });

    it.each(UNAPPROVED)("adding, reordering or removing a non-correct option on a %s key keeps the origin", (origin) => {
      const item = dropdownItem(origin);
      const added = withGapOptions(item, "gap_001", [...OPTIONS, choice("choice_003", "grön")], "choice_001");
      const reordered = withGapOptions(added, "gap_001", [added.gaps[0].options[2], ...OPTIONS], "choice_001");
      const removed = withGapOptions(reordered, "gap_001", [OPTIONS[0], OPTIONS[1]], "choice_001");
      expect(added.answer_key.origin).toBe(origin);
      expect(reordered.answer_key.origin).toBe(origin);
      expect(removed.answer_key.origin).toBe(origin);
      expect(removed.gaps[0].options).toEqual(OPTIONS);
    });

    it("clearing the correct option of the only keyed gap leaves no key", () => {
      const item = dropdownItem("ai_interpreted");
      const onlyKeyed = { ...item, gaps: [item.gaps[0], { ...item.gaps[1], correct_option_id: null }] };
      const result = withGapOptions(onlyKeyed, "gap_001", [...OPTIONS], null);
      expect(result.answer_key.origin).toBe("absent");
    });

    it("clearing the correct option while another gap stays keyed is teacher authored", () => {
      const result = withGapOptions(dropdownItem("ai_interpreted"), "gap_001", [...OPTIONS], null);
      expect(result.answer_key.origin).toBe("teacher_authored");
    });
  });
});
