/** Contract D2/D6/D8: teacher transitions preserve source text and item points. */
import { describe, expect, it } from "vitest";

import type { NativeExamItem } from "../../../api/examWorkspace";
import { hasInvalidAnswerKey } from "./examWorkspaceAnswerKeyRules";
import { examWorkspaceItemReadiness } from "./examWorkspaceItemReadiness";
import { choiceItem, gapItem } from "./examWorkspaceKeyedItems.specSupport";
import {
  reviewed,
  withCorrectChoices,
  withGapAsText,
  withGapValues,
  withoutAutomaticValue,
  withoutInterpretedKey,
  withMatchPairs,
} from "./examWorkspaceItemEdits";
import { buildMatchingItem } from "./examWorkspaceMatchingItem.specSupport";

function interpretedGap(): NativeExamItem {
  const item = gapItem("ai_interpreted", [["gap_001", ["Stockholm", "Sthlm"]], ["gap_002", ["Oslo"]]], null);
  return {
    ...item,
    facit_text: "Sveriges huvudstad är Stockholm och Norges är Oslo.",
    gaps: item.gaps.map((gap, index) => ({ ...gap, automatic_values: index === 0 ? ["Stockhom"] : ["Oslp"] })),
  };
}

describe("conversion answer-key transitions", () => {
  it("keeps interpreted keys export-ready but blocks invented keys until reviewed", () => {
    const interpreted = choiceItem("single_choice", "ai_interpreted", ["choice_001"], null);
    expect(examWorkspaceItemReadiness(interpreted)).toEqual([]);
    expect(examWorkspaceItemReadiness(withoutInterpretedKey(interpreted))).toContain("missing_answer_key");
    const invented = choiceItem("single_choice", "machine_proposed", ["choice_001"], null);
    expect(examWorkspaceItemReadiness(invented)).toContain("machine_proposed_key_unreviewed");
    expect(examWorkspaceItemReadiness(reviewed(invented))).toEqual([]);
  });
  it("undo clears all gap answers, keeps body/points/source facit, and leaves a valid absent key", () => {
    const source = interpretedGap();
    const result = withoutInterpretedKey(source);
    expect(result.answer_key).toEqual({ origin: "absent", correct_choice_ids: [], match_pairs: [] });
    expect(result.gaps.every((gap) => gap.accepted_values.length === 0 && gap.automatic_values.length === 0)).toBe(true);
    expect(result.facit_text).toBe(source.facit_text);
    expect(result.body).toBe(source.body);
    expect(result.points).toBe(source.points);
    expect(hasInvalidAnswerKey(result)).toBe(false);
    expect(source.gaps[0]?.accepted_values).toEqual(["Stockholm", "Sthlm"]);
  });

  it("undo clears choices and matching pairs, but never undoes invented keys", () => {
    const choice = choiceItem("single_choice", "ai_interpreted", ["choice_001"], null);
    expect(withoutInterpretedKey(choice).answer_key.correct_choice_ids).toEqual([]);
    const match = buildMatchingItem();
    match.answer_key.origin = "ai_interpreted";
    expect(withoutInterpretedKey(match).answer_key.match_pairs).toEqual([]);
    const invented = choiceItem("single_choice", "machine_proposed", ["choice_001"], null);
    expect(withoutInterpretedKey(invented)).toBe(invented);
  });

  it.each(["ai_interpreted", "machine_proposed"] as const)("reviewing %s replaces the AI origin", (origin) => {
    const result = reviewed(choiceItem("single_choice", origin, ["choice_001"], null));
    expect(result.answer_key.origin).toBe("reviewed_advisory");
    expect(result.review.state).toBe("review_complete");
    expect(result.answer_key.correct_choice_ids).toEqual(["choice_001"]);
  });

  it("teacher edits replace AI provenance for every key family", () => {
    const choice = choiceItem("single_choice", "ai_interpreted", ["choice_001"], null);
    expect(withCorrectChoices(choice, ["choice_002"]).answer_key.origin).toBe("teacher_authored");
    const match = buildMatchingItem();
    match.answer_key.origin = "ai_interpreted";
    expect(withMatchPairs(match, match.answer_key.match_pairs).answer_key.origin).toBe("teacher_authored");
    const result = withGapValues(interpretedGap(), "gap_001", ["Göteborg"]);
    expect(result.answer_key.origin).toBe("teacher_authored");
    expect(result.gaps[0]?.automatic_values).toEqual(["Stockhom"]);
    expect(result.gaps[1]?.automatic_values).toEqual(["Oslp"]);
  });

  it.each(["ai_interpreted", "machine_proposed", "source_provided"] as const)(
    "removes only the selected automatic answer and preserves %s provenance",
    (origin) => {
      const source = interpretedGap();
      source.answer_key.origin = origin;
      const result = withoutAutomaticValue(source, "gap_001", "Stockhom");
      expect(result.gaps[0]?.automatic_values).toEqual([]);
      expect(result.gaps[0]?.accepted_values).toEqual(["Stockholm", "Sthlm"]);
      expect(result.gaps[1]).toBe(source.gaps[1]);
      expect(result.answer_key).toEqual(source.answer_key);
      expect(examWorkspaceItemReadiness(result)).toEqual(examWorkspaceItemReadiness(source));
      if (origin === "ai_interpreted") {
        expect(withoutInterpretedKey(result).answer_key.origin).toBe("absent");
      }
      expect(source.gaps[0]?.automatic_values).toEqual(["Stockhom"]);
      expect(withoutAutomaticValue(source, "gap_001", "missing")).toBe(source);
    },
  );

  it.each(["ai_interpreted", "machine_proposed", "source_provided"] as const)(
    "turns the selected gap into its first accepted answer with points and %s provenance unchanged",
    (origin) => {
      const source = interpretedGap();
      source.answer_key.origin = origin;
      const result = withGapAsText(source, "gap_001");
      expect(result.body[0]?.segments).toEqual([
        { kind: "text", text: "Hon heter " },
        { kind: "text", text: "Stockholm" },
        { kind: "text", text: " och " },
        { kind: "gap", gap_id: "gap_002" },
        { kind: "text", text: " och " },
      ]);
      expect(result.gaps).toEqual([source.gaps[1]]);
      expect(result.points).toBe(source.points);
      expect(result.answer_key).toEqual(source.answer_key);
      expect(examWorkspaceItemReadiness(result)).toEqual(examWorkspaceItemReadiness(source));
      if (origin === "ai_interpreted") {
        expect(withoutInterpretedKey(result).answer_key.origin).toBe("absent");
      }
      expect(source.gaps).toHaveLength(2);
      expect(hasInvalidAnswerKey(result)).toBe(false);
      expect(withGapAsText(result, "gap_002")).toBe(result);
    },
  );

  it("refuses unknown gaps and gaps with no first accepted value", () => {
    const source = interpretedGap();
    expect(withGapAsText(source, "missing")).toBe(source);
    const empty = withoutInterpretedKey(source);
    expect(withGapAsText(empty, "gap_001")).toBe(empty);
  });
});
