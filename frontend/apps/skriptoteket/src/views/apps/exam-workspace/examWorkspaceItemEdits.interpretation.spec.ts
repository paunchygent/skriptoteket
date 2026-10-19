/** Contract D2/D6/D8: teacher transitions preserve source text and item points. */
import { describe, expect, it } from "vitest";

import type { NativeExamItem } from "../../../api/examWorkspace";
import { hasInvalidAnswerKey } from "./examWorkspaceAnswerKeyRules";
import { examWorkspaceItemReadiness } from "./examWorkspaceItemReadiness";
import { buildGap, choiceItem, gapItem } from "./examWorkspaceKeyedItems.specSupport";
import {
  canUndoInterpretation,
  reviewed,
  withCorrectChoices,
  withoutInterpretedKey,
  withMatchPairs,
} from "./examWorkspaceItemEdits";
import {
  withGapAsText,
  withGapValues,
  withoutAutomaticValue,
} from "./examWorkspaceGapEdits";
import { plainBody } from "./examWorkspaceRichText";
import { placedGapIds } from "./examWorkspaceRichTextDocument";
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
        { kind: "text", marks: [], text: "Hon heter ", kept_gap_id: null },
        { kind: "text", marks: [], text: "Stockholm", kept_gap_id: null },
        { kind: "text", marks: [], text: " och ", kept_gap_id: null },
        { kind: "gap", gap_id: "gap_002" },
        { kind: "text", marks: [], text: " och ", kept_gap_id: null },
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
    },
  );

  it("turns the item's only gap into text and leaves a question with no gap", () => {
    const afterFirst = withGapAsText(interpretedGap(), "gap_001");
    const lastGap = afterFirst.gaps[0]!;

    const result = withGapAsText(afterFirst, lastGap.gap_id);

    expect(result.gaps).toEqual([]);
    expect(placedGapIds(result.body)).toEqual([]);
    expect(result.body[0]?.segments.some((segment) => segment.kind === "gap")).toBe(false);
  });

  it("refuses unknown gaps and gaps with no first accepted value", () => {
    const source = interpretedGap();
    expect(withGapAsText(source, "missing")).toBe(source);
    const empty = withoutInterpretedKey(source);
    expect(withGapAsText(empty, "gap_001")).toBe(empty);
  });
});

describe("undoing an interpreted dropdown key", () => {
  function interpretedDropdown(): NativeExamItem {
    return {
      ...gapItem("ai_interpreted", [], null),
      kind: "inline_choice",
      facit_text: "Rätt är röd.",
      gaps: [
        buildGap("gap_001", [], {
          correct_option_id: "choice_001",
          options: [
            { choice_id: "choice_001", body: plainBody("röd") },
            { choice_id: "choice_002", body: plainBody("blå") },
          ],
        }),
      ],
    };
  }

  it("is not offered and changes nothing", () => {
    const item = interpretedDropdown();
    expect(canUndoInterpretation(item)).toBe(false);
    expect(withoutInterpretedKey(item)).toBe(item);
  });

  it("is offered for an interpreted gap_fill and not for a teacher-authored one", () => {
    expect(canUndoInterpretation(interpretedGap())).toBe(true);
    expect(canUndoInterpretation(gapItem("teacher_authored", [["gap_001", ["x"]]], null))).toBe(false);
  });
});
