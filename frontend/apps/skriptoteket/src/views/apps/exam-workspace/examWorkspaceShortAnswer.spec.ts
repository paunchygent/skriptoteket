/**
 * Exam workspace Kort svar shape rule (L2 option A, user 2026-10-19; L3).
 *
 * Expected behavior:
 *   A gap_fill item reads as Kort svar exactly when its only gap stands alone
 *   as the sole segment of its last paragraph; the Fråga field edits only the
 *   paragraphs before that answer paragraph, so the gap record never drops.
 *   A new Lucktext starts empty with no gap, while a new Kort svar keeps its
 *   one-gap body. The question list labels a Kort svar item "Kort svar".
 */

import { describe, expect, it } from "vitest";

import type { NativeExamBodyParagraph, NativeExamItem } from "../../../api/examWorkspace";
import { newTeacherItem, withBody } from "./examWorkspaceItemEdits";
import { buildGap } from "./examWorkspaceKeyedItems.specSupport";
import { examWorkspaceItemTypeLabel } from "./examWorkspaceRows";
import {
  isShortAnswer,
  shortAnswerParts,
  withShortAnswerQuestion,
} from "./examWorkspaceShortAnswer";
import { plainBody } from "./examWorkspaceRichText";

function gapFillItem(
  body: NativeExamBodyParagraph[],
  gaps: NativeExamItem["gaps"],
  kind: NativeExamItem["kind"] = "gap_fill",
): NativeExamItem {
  return {
    ...newTeacherItem("item_001", 1, "gap_fill"),
    answer_key: { correct_choice_ids: [], match_pairs: [], origin: "absent" },
    body,
    gaps,
    kind,
  };
}

function gapParagraph(gapId: string): NativeExamBodyParagraph {
  return { heading_level: null, segments: [{ kind: "gap", gap_id: gapId }] };
}

describe("shortAnswerParts shape rule", () => {
  it("reads a new short answer as Kort svar and a new Lucktext as not", () => {
    const shortAnswer = newTeacherItem("item_001", 1, "short_answer");
    const parts = shortAnswerParts(shortAnswer);
    expect(parts).not.toBeNull();
    expect(isShortAnswer(shortAnswer)).toBe(true);

    const lucktext = newTeacherItem("item_002", 2, "gap_fill");
    expect(shortAnswerParts(lucktext)).toBeNull();
    expect(isShortAnswer(lucktext)).toBe(false);
    expect(lucktext.body).toEqual([]);
    expect(lucktext.gaps).toEqual([]);
  });

  it("reads question paragraphs plus a lone gap paragraph as Kort svar", () => {
    const question = plainBody("Vad heter huvudstaden?");
    const item = gapFillItem(
      [...question, gapParagraph("gap_001")],
      [buildGap("gap_001", ["Paris"])],
    );

    const parts = shortAnswerParts(item);
    expect(parts?.question).toEqual(question);
    expect(parts?.answer).toEqual(gapParagraph("gap_001"));
    expect(parts?.gap.gap_id).toBe("gap_001");
    expect(isShortAnswer(item)).toBe(true);
  });

  it("returns null for text beside the gap in the last paragraph", () => {
    const item = gapFillItem(
      [...plainBody("Vad heter huvudstaden?"),
        { heading_level: null, segments: [
          { kind: "text", marks: [], text: "Svar: " },
          { kind: "gap", gap_id: "gap_001" },
        ] }],
      [buildGap("gap_001", ["Paris"])],
    );

    expect(shortAnswerParts(item)).toBeNull();
    expect(isShortAnswer(item)).toBe(false);
  });

  it("returns null for a gap in a middle paragraph with text after it", () => {
    const item = gapFillItem(
      [{ heading_level: null, segments: [
        { kind: "text", marks: [], text: "Fyll i " },
        { kind: "gap", gap_id: "gap_001" },
      ] }, ...plainBody("Motivera svaret.")],
      [buildGap("gap_001", ["Paris"])],
    );

    expect(shortAnswerParts(item)).toBeNull();
    expect(isShortAnswer(item)).toBe(false);
  });

  it("returns null for two gaps", () => {
    const item = gapFillItem(
      [...plainBody("Fyll i båda."), gapParagraph("gap_002")],
      [buildGap("gap_001", ["ett"]), buildGap("gap_002", ["två"])],
    );
    const withBothPlaced: NativeExamItem = {
      ...item,
      body: [{ heading_level: null, segments: [
        { kind: "gap", gap_id: "gap_001" },
        { kind: "gap", gap_id: "gap_002" },
      ] }],
    };

    expect(shortAnswerParts(withBothPlaced)).toBeNull();
    expect(isShortAnswer(withBothPlaced)).toBe(false);
  });

  it("returns null for a placed gap without a record and a record without a placed gap", () => {
    const placedWithoutRecord = gapFillItem([gapParagraph("gap_001")], []);
    expect(shortAnswerParts(placedWithoutRecord)).toBeNull();
    expect(isShortAnswer(placedWithoutRecord)).toBe(false);

    const recordWithoutPlaced = gapFillItem(plainBody("Vad heter huvudstaden?"), [buildGap("gap_001")]);
    expect(shortAnswerParts(recordWithoutPlaced)).toBeNull();
    expect(isShortAnswer(recordWithoutPlaced)).toBe(false);
  });

  it("returns null for an inline_choice with the same shape and an empty body", () => {
    const dropdown = gapFillItem(
      [gapParagraph("gap_001")],
      [{ ...buildGap("gap_001"), correct_option_id: "choice_001",
        options: [
          { body: [], choice_id: "choice_001" },
          { body: [], choice_id: "choice_002" },
        ] }],
      "inline_choice",
    );
    expect(shortAnswerParts(dropdown)).toBeNull();
    expect(isShortAnswer(dropdown)).toBe(false);

    expect(shortAnswerParts(gapFillItem([], []))).toBeNull();
    expect(isShortAnswer(gapFillItem([], []))).toBe(false);
  });
});

describe("withShortAnswerQuestion", () => {
  it("keeps the answer paragraph last and identical, and the gap record survives withBody", () => {
    const item = gapFillItem(
      [...plainBody("Gammal fråga?"), gapParagraph("gap_001")],
      [buildGap("gap_001", ["Paris"])],
    );
    const parts = shortAnswerParts(item);
    expect(parts).not.toBeNull();
    const question = plainBody("Vad heter huvudstaden i Frankrike?");

    const next = withShortAnswerQuestion(parts!, question);

    expect(next).toEqual([...question, gapParagraph("gap_001")]);
    const updated = withBody(item, next);
    expect(updated.gaps).toEqual(item.gaps);
    expect(isShortAnswer(updated)).toBe(true);
  });

  it("returns the body unchanged when the question itself places a gap", () => {
    const item = gapFillItem(
      [...plainBody("Gammal fråga?"), gapParagraph("gap_001")],
      [buildGap("gap_001", ["Paris"])],
    );
    const parts = shortAnswerParts(item);
    expect(parts).not.toBeNull();
    const questionWithGap = [gapParagraph("gap_002")];

    expect(withShortAnswerQuestion(parts!, questionWithGap)).toEqual(item.body);
  });

  it("keeps only the answer paragraph for an empty question and stays a Kort svar", () => {
    const item = gapFillItem(
      [...plainBody("Gammal fråga?"), gapParagraph("gap_001")],
      [buildGap("gap_001", ["Paris"])],
    );
    const parts = shortAnswerParts(item);
    expect(parts).not.toBeNull();

    const next = withShortAnswerQuestion(parts!, []);

    expect(next).toEqual([gapParagraph("gap_001")]);
    expect(isShortAnswer({ ...item, body: next })).toBe(true);
  });

  it("splits the question part and names the one gap", () => {
    const question = plainBody("Vad heter huvudstaden?");
    const item = gapFillItem([...question, gapParagraph("gap_001")], [buildGap("gap_001")]);

    const parts = shortAnswerParts(item);
    expect(parts?.question).toEqual(question);
    expect(parts?.gap.gap_id).toBe("gap_001");
  });
});

describe("examWorkspaceItemTypeLabel", () => {
  it("labels a Kort svar item Kort svar, a text-beside-gap Lucktext Lucktext, and a dropdown Lucktext med rullista", () => {
    const shortAnswer = newTeacherItem("item_001", 1, "short_answer");
    expect(examWorkspaceItemTypeLabel(shortAnswer, false)).toBe("Kort svar");

    const lucktextWithTextBesideGap = gapFillItem(
      [{ heading_level: null, segments: [
        { kind: "text", marks: [], text: "Svar: " },
        { kind: "gap", gap_id: "gap_001" },
      ] }],
      [buildGap("gap_001")],
    );
    expect(examWorkspaceItemTypeLabel(lucktextWithTextBesideGap, false)).toBe("Lucktext");

    const dropdown = gapFillItem(
      [gapParagraph("gap_001")],
      [{ ...buildGap("gap_001"), correct_option_id: "choice_001",
        options: [
          { body: [], choice_id: "choice_001" },
          { body: [], choice_id: "choice_002" },
        ] }],
      "inline_choice",
    );
    expect(examWorkspaceItemTypeLabel(dropdown, false)).toBe("Lucktext med rullista");
  });

  it("labels an unbuilt item Ej konverterad even for a Kort svar shape", () => {
    const shortAnswer = newTeacherItem("item_001", 1, "short_answer");
    expect(isShortAnswer(shortAnswer)).toBe(true);
    expect(examWorkspaceItemTypeLabel(shortAnswer, true)).toBe("Ej konverterad");
  });
});
