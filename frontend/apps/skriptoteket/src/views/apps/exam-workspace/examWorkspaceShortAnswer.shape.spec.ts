/**
 * Exam workspace Kort svar / Lucktext shape edits (R4, R5; L2, L6, L10).
 *
 * Expected behavior:
 *   A Kort svar becomes a Lucktext with its answer gap, and its answers, at
 *   the end of the last question paragraph; an eligible Lucktext (at most one
 *   gap) becomes a Kort svar with its gap alone in the last paragraph. Both
 *   are one pure client edit through the existing body and gap-record paths,
 *   with no server change type and no native-format change. Anything else
 *   returns the same item.
 */

import { describe, expect, it } from "vitest";

import type { NativeExamBodyParagraph, NativeExamItem } from "../../../api/examWorkspace";
import { newTeacherItem, withBody } from "./examWorkspaceItemEdits";
import { buildGap } from "./examWorkspaceKeyedItems.specSupport";
import { plainBody } from "./examWorkspaceRichText";
import { bodyFromEditor, editorContentFrom, placedGapIds } from "./examWorkspaceRichTextDocument";
import {
  canBecomeShortAnswer,
  isShortAnswer,
  withGapTextShape,
  withShortAnswerShape,
} from "./examWorkspaceShortAnswer";

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

function kortSvar(question: string): NativeExamItem {
  return gapFillItem(
    [...plainBody(question), gapParagraph("gap_001")],
    [buildGap("gap_001", ["Stockholm"])],
  );
}

describe("withGapTextShape", () => {
  it("moves the answer gap to the end of the question with one space, keeping the gap and its answers", () => {
    const item = kortSvar("Vad heter huvudstaden?");

    const result = withGapTextShape(item);

    expect(result).not.toBe(item);
    expect(isShortAnswer(result)).toBe(false);
    expect(placedGapIds(result.body)).toEqual(["gap_001"]);
    const last = result.body[result.body.length - 1];
    expect(last).toBeDefined();
    if (last === undefined) {
      throw new Error("expected a last paragraph");
    }
    expect(last.segments).toEqual([
      { kind: "text", marks: [], text: "Vad heter huvudstaden?" },
      { kind: "text", marks: [], text: " " },
      { kind: "gap", gap_id: "gap_001" },
    ]);
    expect(result.gaps).toEqual(item.gaps);
    const gap = result.gaps[0];
    expect(gap).toBeDefined();
    if (gap === undefined) {
      throw new Error("expected the gap record");
    }
    expect(gap.accepted_values).toEqual(["Stockholm"]);
  });

  it("adds no extra space when the question already ends in a space", () => {
    const item = kortSvar("Vad heter huvudstaden? ");

    const result = withGapTextShape(item);

    const last = result.body[result.body.length - 1];
    expect(last).toBeDefined();
    if (last === undefined) {
      throw new Error("expected a last paragraph");
    }
    expect(last.segments).toEqual([
      { kind: "text", marks: [], text: "Vad heter huvudstaden? " },
      { kind: "gap", gap_id: "gap_001" },
    ]);
    expect(isShortAnswer(result)).toBe(false);
  });

  it("keeps the gap paragraph first and adds an empty paragraph for an empty question", () => {
    const item = gapFillItem([gapParagraph("gap_001")], [buildGap("gap_001", ["Stockholm"])]);

    const result = withGapTextShape(item);

    expect(result.body).toEqual([gapParagraph("gap_001"), { heading_level: null, segments: [] }]);
    expect(isShortAnswer(result)).toBe(false);
    expect(result.gaps).toEqual(item.gaps);
  });

  it("moves the gap onto the text paragraph when the last question paragraph is empty", () => {
    const item = gapFillItem(
      [...plainBody("Vad heter huvudstaden?"), { heading_level: null, segments: [] }, gapParagraph("gap_001")],
      [buildGap("gap_001", ["Stockholm"])],
    );

    const result = withGapTextShape(item);

    expect(isShortAnswer(result)).toBe(false);
    expect(placedGapIds(result.body)).toEqual(["gap_001"]);
    const last = result.body[result.body.length - 1];
    expect(last).toBeDefined();
    if (last === undefined) {
      throw new Error("expected a last paragraph");
    }
    expect(last.segments).toEqual([
      { kind: "text", marks: [], text: "Vad heter huvudstaden?" },
      { kind: "text", marks: [], text: " " },
      { kind: "gap", gap_id: "gap_001" },
    ]);
    expect(result.gaps).toEqual(item.gaps);
    const mapped = bodyFromEditor(editorContentFrom(result.body));
    expect(isShortAnswer(withBody(result, mapped))).toBe(false);
  });

  it("keeps the gap paragraph first and adds an empty paragraph for a question of one empty paragraph", () => {
    const item = gapFillItem(
      [{ heading_level: null, segments: [] }, gapParagraph("gap_001")],
      [buildGap("gap_001", ["Stockholm"])],
    );

    const result = withGapTextShape(item);

    expect(result.body).toEqual([gapParagraph("gap_001"), { heading_level: null, segments: [] }]);
    expect(isShortAnswer(result)).toBe(false);
    expect(result.gaps).toEqual(item.gaps);
    const mapped = bodyFromEditor(editorContentFrom(result.body));
    expect(isShortAnswer(withBody(result, mapped))).toBe(false);
  });

  it("moves the gap onto the text paragraph when several trailing question paragraphs are empty", () => {
    const item = gapFillItem(
      [...plainBody("Vad heter huvudstaden?"),
        { heading_level: null, segments: [] },
        { heading_level: null, segments: [] },
        gapParagraph("gap_001")],
      [buildGap("gap_001", ["Stockholm"])],
    );

    const result = withGapTextShape(item);

    expect(isShortAnswer(result)).toBe(false);
    expect(placedGapIds(result.body)).toEqual(["gap_001"]);
    const last = result.body[result.body.length - 1];
    expect(last).toBeDefined();
    if (last === undefined) {
      throw new Error("expected a last paragraph");
    }
    expect(last.segments).toEqual([
      { kind: "text", marks: [], text: "Vad heter huvudstaden?" },
      { kind: "text", marks: [], text: " " },
      { kind: "gap", gap_id: "gap_001" },
    ]);
    expect(result.gaps).toEqual(item.gaps);
    const mapped = bodyFromEditor(editorContentFrom(result.body));
    expect(isShortAnswer(withBody(result, mapped))).toBe(false);
  });

  it("returns the same Lucktext item", () => {
    const item = gapFillItem(
      [{ heading_level: null, segments: [
        { kind: "text", marks: [], text: "Huvudstaden är " },
        { kind: "gap", gap_id: "gap_001" },
        { kind: "text", marks: [], text: " i Sverige." },
      ] }],
      [buildGap("gap_001", ["Stockholm"])],
    );

    expect(withGapTextShape(item)).toBe(item);
  });
});

describe("withShortAnswerShape", () => {
  it("moves the inline gap to its own last paragraph, keeping the text and the answers", () => {
    const item = gapFillItem(
      [{ heading_level: null, segments: [
        { kind: "text", marks: [], text: "Huvudstaden är " },
        { kind: "gap", gap_id: "gap_001" },
        { kind: "text", marks: [], text: " i Sverige." },
      ] }],
      [buildGap("gap_001", ["Stockholm"])],
    );

    const result = withShortAnswerShape(item);

    expect(result).not.toBe(item);
    expect(isShortAnswer(result)).toBe(true);
    expect(result.body).toEqual([
      { heading_level: null, segments: [
        { kind: "text", marks: [], text: "Huvudstaden är " },
        { kind: "text", marks: [], text: " i Sverige." },
      ] },
      gapParagraph("gap_001"),
    ]);
    expect(result.gaps).toEqual(item.gaps);
    const inlineGap = result.gaps[0];
    expect(inlineGap).toBeDefined();
    if (inlineGap === undefined) {
      throw new Error("expected the gap record");
    }
    expect(inlineGap.accepted_values).toEqual(["Stockholm"]);
  });

  it("drops a paragraph that held only the gap", () => {
    const item = gapFillItem(
      [...plainBody("Fråga."), gapParagraph("gap_001")],
      [buildGap("gap_001", ["Stockholm"]), buildGap("gap_002", ["extra"])],
    );
    const onlyGapPlaced: NativeExamItem = {
      ...item,
      body: [...plainBody("Fråga."), gapParagraph("gap_001")],
      gaps: [buildGap("gap_001", ["Stockholm"])],
    };

    const result = withShortAnswerShape(onlyGapPlaced);

    expect(result.body).toEqual([...plainBody("Fråga."), gapParagraph("gap_001")]);
    expect(isShortAnswer(result)).toBe(true);
  });

  it("creates a new empty gap_001 alone in the last paragraph for a Lucktext with no gap", () => {
    const item = gapFillItem(plainBody("Berätta om Stockholm."), []);

    const result = withShortAnswerShape(item);

    expect(isShortAnswer(result)).toBe(true);
    expect(result.body).toEqual([...plainBody("Berätta om Stockholm."), gapParagraph("gap_001")]);
    expect(result.gaps).toHaveLength(1);
    const createdGap = result.gaps[0];
    expect(createdGap).toBeDefined();
    if (createdGap === undefined) {
      throw new Error("expected the gap record");
    }
    expect(createdGap.gap_id).toBe("gap_001");
    expect(createdGap.accepted_values).toEqual([]);
  });

  it("returns the same item for two gaps, a dropdown, free text and an already Kort svar item", () => {
    const twoGaps = gapFillItem(
      [{ heading_level: null, segments: [
        { kind: "gap", gap_id: "gap_001" },
        { kind: "gap", gap_id: "gap_002" },
      ] }],
      [buildGap("gap_001", ["ett"]), buildGap("gap_002", ["två"])],
    );
    expect(withShortAnswerShape(twoGaps)).toBe(twoGaps);
    expect(canBecomeShortAnswer(twoGaps)).toBe(false);

    const dropdown = gapFillItem(
      [gapParagraph("gap_001")],
      [{ ...buildGap("gap_001"), correct_option_id: "choice_001",
        options: [
          { body: [], choice_id: "choice_001" },
          { body: [], choice_id: "choice_002" },
        ] }],
      "inline_choice",
    );
    expect(withShortAnswerShape(dropdown)).toBe(dropdown);
    expect(canBecomeShortAnswer(dropdown)).toBe(false);

    const freeText: NativeExamItem = { ...kortSvar("Vad heter huvudstaden?"), kind: "free_text" };
    expect(withShortAnswerShape(freeText)).toBe(freeText);
    expect(canBecomeShortAnswer(freeText)).toBe(false);

    const already = kortSvar("Vad heter huvudstaden?");
    expect(withShortAnswerShape(already)).toBe(already);
    expect(canBecomeShortAnswer(already)).toBe(false);
  });
});

describe("shape round trip", () => {
  it("returns a Kort svar with the same gap and answers", () => {
    const item = kortSvar("Vad heter huvudstaden?");

    const roundTripped = withShortAnswerShape(withGapTextShape(item));

    expect(isShortAnswer(roundTripped)).toBe(true);
    expect(roundTripped.gaps).toEqual(item.gaps);
    // The inserted separator space stays its own run, as `withGapAsText`
    // leaves converted runs unmerged; the question still reads the same.
    expect(roundTripped.body).toHaveLength(item.body.length);
    expect(roundTripped.body[roundTripped.body.length - 1]).toEqual(
      item.body[item.body.length - 1],
    );
    const questionText = roundTripped.body
      .slice(0, -1)
      .flatMap((paragraph) =>
        paragraph.segments.flatMap((segment) => (segment.kind === "text" ? [segment.text] : [])),
      )
      .join("");
    expect(questionText).toBe("Vad heter huvudstaden? ");
    expect(withBody(item, roundTripped.body).gaps).toEqual(item.gaps);
  });
});
