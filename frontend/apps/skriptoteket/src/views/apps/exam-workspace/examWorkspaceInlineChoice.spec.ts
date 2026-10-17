import { describe, expect, it } from "vitest";

import type { NativeExamItem } from "../../../api/examWorkspace";
import { buildFreeTextItem } from "../../../test/examWorkspaceFixtures";
import { hasInvalidAnswerKey } from "./examWorkspaceAnswerKeyRules";
import { newTeacherItem } from "./examWorkspaceItemEdits";
import { buildGap } from "./examWorkspaceKeyedItems.specSupport";
import { plainBody } from "./examWorkspaceRichText";
import { toExamWorkspaceItemRows } from "./examWorkspaceRows";

function inlineChoiceItem(overrides: Partial<NativeExamItem> = {}): NativeExamItem {
  return buildFreeTextItem(1, {
    kind: "inline_choice",
    body: [{ heading_level: null, segments: [
      { kind: "gap", gap_id: "gap_001" },
      { kind: "gap", gap_id: "gap_002" },
    ] }],
    answer_key: { correct_choice_ids: [], match_pairs: [], origin: "source_provided" },
    gaps: ["gap_001", "gap_002"].map((gapId) => buildGap(gapId, [], {
      options: [
        { choice_id: "option_001", body: plainBody("Rätt") },
        { choice_id: "option_002", body: plainBody("Fel") },
      ],
      correct_option_id: "option_001",
    })),
    ...overrides,
  });
}

describe("inline-choice answer keys", () => {
  it("accepts a selected option in every gap, with option ids scoped to each gap", () => {
    expect(hasInvalidAnswerKey(inlineChoiceItem())).toBe(false);
  });

  it.each([null, "undeclared"])("rejects a gap whose selected option is %j", (correctOptionId) => {
    const item = inlineChoiceItem();
    item.gaps[1]!.correct_option_id = correctOptionId;
    expect(hasInvalidAnswerKey(item)).toBe(true);
  });

  it("rejects an option declared only in another gap", () => {
    const item = inlineChoiceItem();
    item.gaps[0]!.options[0]!.choice_id = "other-gap-only";
    item.gaps[0]!.correct_option_id = "other-gap-only";
    item.gaps[1]!.correct_option_id = "other-gap-only";
    expect(hasInvalidAnswerKey(item)).toBe(true);
  });

  it("rejects selected gap options when the key claims to be absent", () => {
    const item = inlineChoiceItem();
    item.answer_key.origin = "absent";
    expect(hasInvalidAnswerKey(item)).toBe(true);
  });

  it("keys gaps, not top-level choices", () => {
    const item = inlineChoiceItem();
    item.choices = [{ choice_id: "choice_001", body: plainBody("Ett val") }];
    item.answer_key.correct_choice_ids = ["choice_001"];
    expect(hasInvalidAnswerKey(item)).toBe(true);
  });
});

describe("inline-choice row label", () => {
  it("uses the approved dropdown Lucktext kind name in the teacher's row", () => {
    expect(toExamWorkspaceItemRows([inlineChoiceItem()])[0]?.typeLabel).toBe("Lucktext med rullista");
  });
});

describe("new teacher item current-schema fields", () => {
  it("starts a short typed answer with empty option data, not a dropdown key", () => {
    const item = newTeacherItem("new-question", 2, "short_answer");
    expect(item.kind).toBe("gap_fill");
    expect(item.import_record).toBeNull();
    expect(item.gaps).toEqual([{
      gap_id: "gap_001",
      accepted_values: [],
      automatic_values: [],
      excluded_automatic_values: [],
      options: [],
      correct_option_id: null,
    }]);
    expect(hasInvalidAnswerKey(item)).toBe(false);
  });

  it("starts free text without gaps or an import record", () => {
    const item = newTeacherItem("new-question", 2, "free_text");
    expect(item.gaps).toEqual([]);
    expect(item.import_record).toBeNull();
    expect(hasInvalidAnswerKey(item)).toBe(false);
  });
});
