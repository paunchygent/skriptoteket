import { describe, expect, it } from "vitest";

import type { NativeExamItem } from "../../../api/examWorkspace";
import {
  examWorkspaceItemReadiness,
  examWorkspaceReadinessByItemId,
} from "./examWorkspaceItemReadiness";
import { buildChoiceItem } from "./examWorkspaceItemReadiness.specSupport";
import { plainBody } from "./examWorkspaceRichText";

describe("ordering readiness", () => {
  function ordering(texts: string[], printOrder: string[] = []): NativeExamItem {
    const choices = texts.map((text, index) => ({
      choice_id: `choice_00${index + 1}`,
      body: plainBody(text),
    }));
    return buildChoiceItem({
      answer_key: { correct_choice_ids: [], match_pairs: [], origin: "teacher_authored" },
      choices,
      kind: "ordering",
      print_order: printOrder,
    });
  }

  it("accepts two or more filled steps with any print order and never asks for a key", () => {
    expect(examWorkspaceItemReadiness(ordering(["Först", "Sedan"], ["choice_002", "choice_001"]))).toEqual([]);
    expect(examWorkspaceItemReadiness(ordering(["A", "B", "C"], ["choice_001", "choice_002", "choice_003"]))).toEqual([]);
    expect(examWorkspaceItemReadiness(ordering(["A", "B"]))).toEqual([]);
  });

  it.each([[[]], [["Ensam"]]])("blocks an ordering question with %j steps as too few", (texts) => {
    const reasons = examWorkspaceItemReadiness(ordering(texts));
    expect(reasons).toEqual(["ordering_too_few_steps"]);
    expect(examWorkspaceReadinessByItemId([ordering(texts)]).item_001).toEqual([
      "Ordningsfrågan behöver minst två steg.",
    ]);
  });

  it.each(["", " \n\t "])("names an empty step %j as an ordering step, not a choice", (blank) => {
    const item = ordering(["Först", blank, "Sist"]);
    expect(examWorkspaceItemReadiness(item)).toEqual(["empty_ordering_step"]);
    expect(examWorkspaceReadinessByItemId([item]).item_001).toEqual([
      "Ett steg i ordningsfrågan saknar text.",
    ]);
  });

  it("reports both reasons for a single blank step and never missing_answer_key", () => {
    const item = ordering([" "]);
    item.answer_key.origin = "teacher_authored";
    expect(examWorkspaceItemReadiness(item)).toEqual(["ordering_too_few_steps", "empty_ordering_step"]);
    expect(examWorkspaceItemReadiness(item)).not.toContain("missing_answer_key");
  });

  it("keeps empty_choice for a single_choice question", () => {
    const item = buildChoiceItem();
    item.choices[1]!.body = plainBody(" ");
    expect(examWorkspaceItemReadiness(item)).toEqual(["empty_choice"]);
  });
});
